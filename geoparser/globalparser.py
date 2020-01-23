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
                    'America': 6252001,
                    'EU': 6255148,
                    'UAE': 290557,
                    'D.C.': 4140963}

  def __init__(self, keep_defaults=False):
    self.key = 'globaldef' if keep_defaults else 'global'
    self.keep_defaults = keep_defaults
    self.matcher = NameMatcher()

    countries = Gazetteer.countries()

    self.top_level_topos = {}
    #self.top_level_topos.update(Gazetteer.admins())
    #self.top_level_topos.update(Gazetteer.us_states())
    self.top_level_topos.update(countries)

    for toponym, demonyms in Gazetteer.demonyms().items():
      if toponym not in countries:
        continue
      for demonym in demonyms:
        self.top_level_topos[demonym] = countries[toponym]

    self.top_level_topos.update(Gazetteer.oceans())
    self.top_level_topos.update(Gazetteer.continents())
    self.top_level_topos.update(self.common_abbrevs)

    self.lookup_tree = {}
    for toponym in self.top_level_topos:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

    self.candidates = {}

  def annotate(self, doc):
    resolutions = {}

    for a in doc.get_all(Layer.topo):
      if a.phrase in self.top_level_topos:
        geoname_id = self.top_level_topos[a.phrase]
        default = Datastore.get_geoname(geoname_id)
      else:
        candidates = self._select_candidates(a.phrase)
        if len(candidates) == 0:
          continue
        default = self._city_result(a.phrase, candidates[0])

      print(f'gres - chose {default} for "{a.phrase}"')
      resolutions[a.phrase] = default

    self._find_missed_top_levels(doc, resolutions)

    should_continue = len(resolutions) > 1 and not self.keep_defaults
    rounds = 0
    while should_continue:
      rounds += 1
      should_continue = False
      tree = GeoNamesTree(resolutions)

      for adm1 in tree.adm1s:
        if tree.adm1_supported(adm1):
          continue
        (toponym, geoname) = list(adm1.geonames.items())[0] # only one in node
        new = self._select_heuristically(toponym, geoname, tree)
        if new != None:
          should_continue = True
          city = self._city_result(toponym, new)
          resolutions[toponym] = city
          print(f'gres - heuristic preferred {city} for {toponym}')
          break
    
    for a in doc.get_all(Layer.topo):
      if a.phrase in resolutions:
        geoname = resolutions[a.phrase]
        doc.annotate(Layer.gres, a.pos, a.phrase, 'global', geoname.id)

  def _find_missed_top_levels(self, doc, resolutions):
    topo_indices = doc.annotations_by_index(Layer.topo)

    def lookup(prefix):
      key = prefix[:2]
      if key not in self.lookup_tree:
        return []
      toponyms = self.lookup_tree[key]
      return [t for t in toponyms if t.startswith(prefix)]

    def commit(c):
      indices = range(c.pos, c.end)
      overlaps = [i for i in topo_indices if i in indices]
      if len(overlaps) > 0:
        return False
      geoname_id = self.top_level_topos[c.lookup_phrase]
      resolutions[c.match] = Datastore.get_geoname(geoname_id)
      return True

    self.matcher.find_matches(doc, lookup, commit)

  def _select_candidates(self, toponym):
    if toponym in self.candidates:
      return self.candidates[toponym]
    results = Datastore.search_geonames(toponym)
    base_name = self._base_name(toponym)
    parts = len(toponym.split(' '))
    candidates = []
    for g in results:
      base = self._base_name(g.name)
      base_topo = self._base_name(g.toponym_name)
      if base_name not in base and base_name not in base_topo:
        continue
      g_parts = len(g.name.split(' '))
      if g_parts > parts and g.population == 0:
        continue
      candidates.append(g)
    if len(candidates) == 0 and len(results) > 0 and results[0].is_city:
      candidates.append(results[0])
      print(f'gres - chose first non-matching cadidate for "{toponym}": {results[0]}')
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

    candidates = sorted(candidates, key=lambda g: -g.population)

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
