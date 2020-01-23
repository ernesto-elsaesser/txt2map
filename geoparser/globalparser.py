import re
from unidecode import unidecode
from .datastore import Datastore
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .gazetteer import Gazetteer
from .tree import GeoNamesTree


class GlobalGeoparser(Step):

  layers = [Layer.gres]

  common_abbrevs = {'U.S.': 6252001,
                    'US': 6252001,
                    'USA': 6252001,
                    'EU': 6255148,
                    'UAE': 290557,
                    'D.C.': 4140963}

  def __init__(self, keep_defaults=False):
    self.key = 'globaldef' if keep_defaults else 'global'
    self.keep_defaults = keep_defaults
    self.matcher = NameMatcher()

    countries = Gazetteer.countries()
    admins = Gazetteer.admins()
    cities = Gazetteer.cities()

    self.common_topos = {}
    self.common_topos.update(admins)
    self.common_topos.update(cities)
    self.common_topos.update(Gazetteer.us_states())

    for toponym, demonyms in Gazetteer.demonyms().items():
      if toponym not in countries:
        continue
      for demonym in demonyms:
        self.common_topos[demonym] = countries[toponym]

    self.common_topos.update(countries)
    self.common_topos.update(Gazetteer.oceans())
    self.common_topos.update(Gazetteer.continents())
    self.common_topos.update(common_abbrevs)

    self.lookup_tree = {}
    stopwords = Gazetteer.stopwords()
    for toponym in self.common_topos:
      if toponym in stopwords:
        continue
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

    self.candidates = {}

  def annotate(self, doc):
    resolutions = self._resolve_defaults(doc)

    unresolved = set()
    for a in doc.get_all(Layer.topo):
      if a.data not in resolutions:
        unresolved.add(a.phrase)
    
    for toponym in unresolved:
      candidates = self._select_candidates(toponym)
      if len(candidates) == 0:
        continue
      city = self._city_result(toponym, candidates[0])
      resolutions[toponym] = city

    should_continue = not self.keep_defaults
    rounds = 0
    while should_continue:
      rounds += 1
      should_continue = False

      tree = GeoNamesTree(resolutions)
      if len(tree.adm1s) < 2:
        break

      for adm1 in tree.adm1s:
        if tree.adm1_supported(adm1):
          continue
        (toponym, geoname) = list(adm1.geonames.items())[0] # only one in node
        new = self._select_heuristically(toponym, geoname, tree)
        if new != None:
          should_continue = True
          city = self._city_result(toponym, new)
          resolutions[toponym] = city
          print(f'Chose {city} over {geoname} for {toponym}')
          break
    
    for a in doc.get_all(Layer.topo):
      if a.phrase in resolutions:
        geoname = resolutions[a.phrase]
        doc.annotate(Layer.gres, a.pos, a.phrase, 'global', geoname.id)


  def _resolve_defaults(self, doc):
    resolutions = {}

    def lookup(prefix):
      key = prefix[:2]
      if key not in self.lookup_tree:
        return []
      toponyms = self.lookup_tree[key]
      return [t for t in toponyms if t.startswith(prefix)]

    def commit(c):
      geoname_id = self.common_topos[c.lookup_phrase]
      resolutions[c.match] = Datastore.get_geoname(geoname_id)
      return True

    self.matcher.find_matches(doc, lookup, commit)

    return resolutions


  def _select_candidates(self, toponym):
    if toponym in self.candidates:
      return self.candidates[toponym]
    results = Datastore.search_geonames(toponym)
    base_name = self._base_name(toponym)
    parts = len(toponym.split(' '))
    candidates = []
    for g in results:
      base = self._base_name(toponym)
      base_topo = self._base_name(g.toponym_name)
      if base_name not in base and base_name not in base_topo:
        continue
      g_parts = len(g.name.split(' '))
      if g_parts > parts and g.population == 0:
        continue
      candidates.append(g)
    if len(candidates) == 0 and len(results) > 0 and results[0].is_city:
      candidates.append(results[0])
      print(f'Chose first non-matching cadidate for "{toponym}": {results[0]}')
    candidates = sorted(candidates, key=lambda g: -g.population)
    self.candidates[toponym] = candidates
    return candidates

  def _base_name(self, toponym):
    toponym = toponym.rstrip('.')
    try:
      toponym = unidecode(toponym)
    except:
      pass
    return toponym.lower()

  def _select_heuristically(self, toponym, current, tree):
    candidates = self._select_candidates(toponym)
    candidates = [c for c in candidates if c.id != current.id]

    if len(candidates) == 0:
      return None

    for g in candidates[:10]:
      node = tree.node_for(g, False)
      if node != None and toponym not in node.geonames:
        return g

    return None

  def _city_result(self, toponym, selected):
    if selected.is_city or selected.adm1 == '-':
      return selected

    name = selected.name
    region = selected.region()
    results = Datastore.search_geonames(toponym)
    for g in results:
      if not g.is_city:
        continue
      if not g.region() == region:
        continue
      if g.name in name or name in g.name:
        return g

    return selected
