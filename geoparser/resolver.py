import re
from .geonames import GeoNamesCache
from .gazetteer import Gazetteer
from .tree import GeoNamesTree
from .config import Config


class GeoNamesResolver:

  def __init__(self, keep_defaults=False):
    self.keep_defaults = keep_defaults
    self.gns_cache = GeoNamesCache()
    self.defaults = Gazetteer.defaults()

  def annotate_rec_res(self, doc):
    self.candidates = {}

    api_defaults = {}
    for a in doc.get_all('rec'):
      if a.data in self.defaults:
        group = 'top'
        default_id = self.defaults[a.data]
      else:
        group = 'api'
        toponym = a.phrase
        if toponym in api_defaults:
          default_id = api_defaults[toponym]
        else:
          candidates = self._select_candidates(toponym)
          if len(candidates) == 0:
            continue
          default = self._city_result(toponym, candidates[0])
          self._resolve_new_ancestors(default, doc)
          default_id = default.id
          api_defaults[toponym] = default_id

      doc.annotate('res', a.pos, a.phrase, group, default_id)

    changed = not self.keep_defaults
    rounds = 0
    max_rounds = Config.resol_max_onto_sim_rounds
    while changed and rounds < max_rounds:
      rounds += 1
      changed = False

      tree = GeoNamesTree(doc)
      unsupported = tree.find_unsupported_adm1s()

      id_map = {}
      for adm1 in unsupported:
        (toponym, old_geoname) = list(adm1.geonames.items())[0]
        new_geoname = self._select_heuristically(toponym, old_geoname, tree)
        if new_geoname != None:
          changed = True
          city = self._city_result(toponym, new_geoname)
          for pos in adm1.positions[toponym]:
            doc.update_annotation('res', pos, 'heu', city.id)
          print(f'Chose {city} over {old_geoname} for {toponym}')

  def _select_candidates(self, toponym):
    if toponym in self.candidates:
      return self.candidates[toponym]
    results = self.gns_cache.search(toponym)
    parts = len(toponym.split(' '))
    candidates = []
    for g in results:
      if toponym not in g.name and toponym not in g.toponym_name:
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

  def _resolve_new_ancestors(self, geoname, doc):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    pop_limit = Config.gazetteer_population_limit
    not_gaz = [g for g in hierarchy[:-1] if g.population <= pop_limit]
    for ancestor in not_gaz:
      name = ancestor.name
      if name in geoname.name:
        continue
      for match in re.finditer(name, doc.text):
        pos = match.start()
        doc.annotate('rec', pos, name, 'anc', name)
        doc.annotate('res', pos, name, 'anc', ancestor.id)

  def _select_heuristically(self, toponym, current, tree):

    candidates = self._select_candidates(toponym)

    if len(candidates) == 1 and current.id == candidates[0].id:
      return None

    cur_hierarchy = self.gns_cache.get_hierarchy(current.id)
    max_depth = len(cur_hierarchy) + 2

    for g in candidates[:10]:

      key_path = tree.key_path(g)
      node = tree.root.get(key_path, False)

      if node == None or toponym in node.geonames:
        continue

      hierarchy = self.gns_cache.get_hierarchy(g.id)
      depth = len(hierarchy)
      if depth <= max_depth:
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
