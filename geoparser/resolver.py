import re
from .geonames import GeoNamesCache
from .gazetteer import Gazetteer
from .recognizer import GazetteerRecognizer
from .tree import GeoNamesTree
from .config import Config


class GeoNamesResolver:

  def __init__(self, keep_defaults=False):
    self.keep_defaults = keep_defaults
    self.recognizer = GazetteerRecognizer()
    self.gns_cache = GeoNamesCache()
    self.candidates = {}

  def annotate_rec_evi_res(self, doc):
    resolutions = {}

    demonyms = self.recognizer.find_demonyms(doc)
    for toponym, geoname_id in demonyms.items():
      resolutions[toponym] = self.gns_cache.get(geoname_id)

    tops = self.recognizer.find_top_level_toponyms(doc)
    for toponym, geoname_id in tops.items():
      resolutions[toponym] = self.gns_cache.get(geoname_id)

    unresolved = set()
    for a in doc.get_all('ner', 'loc'):
      if a.phrase not in resolutions:
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
        if tree.is_supported(adm1):
          continue
        (toponym, geoname) = list(adm1.geonames.items())[0]
        new = self._select_heuristically(toponym, geoname, tree)
        if new != None:
          should_continue = True
          city = self._city_result(toponym, new)
          resolutions[toponym] = city
          print(f'Chose {city} over {geoname} for {toponym}')
          break
    
    ner_anns = doc.annotations_by_position('ner', 'loc')
    resolved = sorted(resolutions.keys(), key=lambda t: -len(t))  # longer first
    for toponym in resolved:
      geoname = resolutions[toponym]
      esc_topo = re.escape(toponym)
      for match in re.finditer(f'\\b{esc_topo}', doc.text):
        pos = match.start()
        doc.annotate('evi', pos, toponym, 'evi', geoname.id, allow_overlap=True)
        if pos in ner_anns:
          ann = ner_anns[pos]
          if len(toponym) >= len(ann.phrase):
            doc.annotate('rec', pos, toponym, 'glo', '')
            doc.annotate('res', pos, toponym, 'glo', geoname.id)
        else:
          node = tree.node_for(geoname, False)
          if tree.is_supported(node):
            print("ADDING NON-NER TOPO: " + toponym)
            doc.annotate('rec', pos, toponym, 'glo', '')
            doc.annotate('res', pos, toponym, 'glo', geoname.id)


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
