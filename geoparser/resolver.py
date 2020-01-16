import re
from .geonames import GeoNamesCache
from .gazetteer import Gazetteer
from .recognizer import GazetteerRecognizer
from .tree import GeoNamesTree
from .config import Config


class GeoNamesResolver:

  common_abbrevs = {'U.S.': 6252001,
                    'US': 6252001,
                    'USA': 6252001,
                    'EU': 6255148,
                    'UAE': 290557,
                    'D.C.': 4140963}

  def __init__(self, keep_defaults=False):
    self.keep_defaults = keep_defaults
    self.recognizer = GazetteerRecognizer()
    self.gns_cache = GeoNamesCache()
    self.matcher = NameMatcher()

    self.defaults = Gazetteer.defaults()
    self.demonyms = {}
    for toponym, demonyms in Gazetteer.demonyms().items():
      if toponym not in self.defaults:
        continue
      for demonym in demonyms:
        self.demonyms[demonym] = self.defaults[toponym]

    self.candidates = {}

  def annotate_res(self, doc):
    resolutions = {}

    def add_demonym(c):
      geoname_id = self.demonyms[c.lookup_phrase]
      resolutions[c.match] = self.gns_cache.get(geoname_id)
      return True

    self.matcher.find_matches(doc, self._lookup_demonym, add_demonym)

    for abbr in self.common_abbrevs:
      match = re.search('\\b' + abbr, doc.text)
      if match != None:
        resolutions[abbr] = self.common_abbrevs[abbr]

    unresolved = set()
    for a in doc.get_all('rec'):
      if a.phrase in self.defaults:
        resolutions[a.phrase] = self.gns_cache.get(self.defaults[a.phrase])
      elif a.phrase not in self.demonyms:
        unresolved.add(a.phrase)
    
    for toponym in unresolved:
      candidates = self._select_candidates(toponym)
      if len(candidates) == 0:
        continue
      city = self._city_result(toponym, candidates[0])
      resolutions[toponym] = city

    should_continue = True
    rounds = 0
    while should_continue:
      rounds += 1
      should_continue = False

      tree = GeoNamesTree(resolutions)
      if self.keep_defaults or len(tree.adm1s) < 2:
        break

      for adm1 in tree.adm1s:
        if tree.adm1_supported(adm1):
          continue
        (toponym, geoname) = list(adm1.geonames.items())[0]
        new = self._select_heuristically(toponym, geoname, tree)
        if new != None:
          should_continue = True
          city = self._city_result(toponym, new)
          resolutions[toponym] = city
          print(f'Chose {city} over {geoname} for {toponym}')
          break
    
    for a in doc.get_all('rec'):
      if a.phrase in resolutions:
        geoname = resolutions[a.phrase]
        doc.annotate('res', pos, toponym, 'glo', geoname.id)

  def _lookup_demonym(self, prefix):
    return [d for d in self.demonyms if d.startswith(prefix)]

  def _select_candidates(self, toponym):
    if toponym in self.candidates:
      return self.candidates[toponym]
    results = self.gns_cache.search(toponym)
    parts = len(toponym.split(' '))
    candidates = []
    for g in results:
      str_topo = toponym.rstrip('.')
      if str_topo not in g.name and str_topo not in g.toponym_name:
        continue
      g_parts = len(g.name.split(' '))
      if g_parts > parts and g.population == 0:
        continue
      candidates.append(g)
    if len(candidates) == 0 and len(results) == 1:
      only = results[0]
      if only.population > 0 or only.is_city:
        candidates.append(only)
        print(f'Chose single non-matching cadidate for "{toponym}": {only}')
    candidates = sorted(candidates, key=lambda g: -g.population)
    self.candidates[toponym] = candidates
    return candidates

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
    results = self.gns_cache.search(toponym)
    for g in results:
      if not g.is_city:
        continue
      if not g.region() == region:
        continue
      if g.name in name or name in g.name:
        return g

    return selected
