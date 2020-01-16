import re
from unidecode import unidecode
from .geonames import GeoNamesCache
from .matcher import NameMatcher
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

    def commit_demonym(c):
      geoname_id = self.demonyms[c.lookup_phrase]
      resolutions[c.match] = self.gns_cache.get(geoname_id)
      return True

    self.matcher.find_matches(doc, self._lookup_demonym, commit_demonym)

    def commit_abbrev(c):
      geoname_id = self.common_abbrevs[c.lookup_phrase]
      resolutions[c.match] = self.gns_cache.get(geoname_id)
      return True

    self.matcher.find_matches(doc, self._lookup_abbrev, commit_abbrev)

    unresolved = set()
    for a in doc.get_all('rec'):
      if a.data in self.defaults:
        resolutions[a.phrase] = self.gns_cache.get(self.defaults[a.data])
      elif a.data not in self.demonyms and a.data not in self.common_abbrevs:
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
        doc.annotate('res', a.pos, a.phrase, 'glo', geoname.id)

  def _lookup_demonym(self, prefix):
    return [d for d in self.demonyms if d.startswith(prefix)]

  def _lookup_abbrev(self, prefix):
    if prefix in self.common_abbrevs:
      return [prefix]
    else:
      return []

  def _select_candidates(self, toponym):
    if toponym in self.candidates:
      return self.candidates[toponym]
    results = self.gns_cache.search(toponym)
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
    results = self.gns_cache.search(toponym)
    for g in results:
      if not g.is_city:
        continue
      if not g.region() == region:
        continue
      if g.name in name or name in g.name:
        return g

    return selected
