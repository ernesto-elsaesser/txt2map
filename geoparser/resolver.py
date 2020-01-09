import os
import re
import json
import pylev
from .document import Document
from .geonames import GeoNamesCache, GeoNamesAPI
from .gazetteer import Gazetteer
from .config import Config


class GeoNamesResolver:

  def __init__(self, gazetteer):
    self.gaz = gazetteer
    self.gns_cache = GeoNamesCache()

  def annotate(self, doc):
    self.candidates = {}

    api_defaults = {}
    for a in doc.get('rec'):
      if a.data in self.gaz.defaults:
        group = 'top'
        default_id = self.gaz.defaults[a.data]
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

    changed = True
    rounds = 0
    max_rounds = Config.resol_max_onto_sim_rounds
    while changed and rounds < max_rounds:
      rounds += 1
      changed = False

      (root, adm1s) = self._make_tree(doc)
      unsupported = self._find_unsupported_adm1s(adm1s)

      id_map = {}
      for adm1 in unsupported:
        (toponym, old_geoname) = list(adm1.geonames.items())[0]
        new_geoname = self._select_heuristically(toponym, old_geoname, root)
        if new_geoname != None:
          changed = True
          city = self._city_result(toponym, new_geoname)
          for pos in adm1.positions[toponym]:
            doc.update_annotation_data('res', pos, city.id)
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
    if len(candidates) == 0 and len(results) == 1 and results[0].population > 0:
      only = results[0]
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
      for match in re.finditer(name, doc.text()):
        pos = match.start()
        doc.annotate('rec', pos, name, 'anc', name)
        doc.annotate('res', pos, name, 'anc', ancestor.id)

  def _make_tree(self, doc):
    root = TreeNode(None, None)
    adm1s = []
    for a in doc.get('res'):
      geoname = self.gns_cache.get(a.data)
      key_path = self._key_path(geoname)
      node = root.get(key_path, True)
      node.add(a.phrase, geoname, a.pos)
      if len(key_path) == 3 and node not in adm1s:
        adm1s.append(node)
    return (root, adm1s)

  def _key_path(self, g):
    cont_name = self.gaz.continent_name(g)
    key_path = [cont_name]
    if g.cc != "-":
      key_path.append(g.cc)
      if g.adm1 != "-" and g.adm1 != "00":
        key_path.append(g.adm1)
    return key_path

  def _find_unsupported_adm1s(self, adm1s):
    if len(adm1s) < 2:
      return []

    unsupported = []
    for node in adm1s:
      support = [len(n.geonames) for n in node.iter()]
      if sum(support) > 2 or support[0] > 1:
        continue # multiple support or siblings
      if support[2] == 1 and len(node.parent.parent.children) == 1:
        continue # exclusive continent
      if support[1] == 1 and len(node.parent.children) == 1:
        continue # exclusive country
      unsupported.append(node)

    return unsupported

  def _select_heuristically(self, toponym, current, root):

    candidates = self._select_candidates(toponym)

    if len(candidates) == 1 and current.id == candidates[0].id:
      return None

    cur_hierarchy = self.gns_cache.get_hierarchy(current.id)
    max_depth = len(cur_hierarchy) + 2

    for g in candidates[:10]:

      key_path = self._key_path(g)
      node = root.get(key_path, False)

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

  def annotate_clusters(self, doc):
    (root, _) = self._make_tree(doc)

    leafs = []
    for cont in root.children.values():
      if len(cont.children) == 0:
        leafs.append(cont)
      for country in cont.children.values():
        if len(country.children) == 0:
          leafs.append(country)
        for adm1 in country.children.values():
          leafs.append(adm1)

    clusters = {}
    for idx, leaf in enumerate(leafs):

      tupels = list(leaf.geonames.items())
      anchors = [g for _, g in tupels if g.is_city]
      if len(anchors) == 0:
        (toponym, geoname) = min(tupels, key=lambda t: t[1].population)
        anchor = self._find_anchor(toponym, geoname)
        if anchor != None:
          anchors.append(anchor)

      cluster_key = f'cl{idx+1}'
      geoname_ids = [g.id for _, g in tupels]
      for node in leaf.iter():
        for phrase, positions in node.positions.items():
          for pos in positions:
            doc.annotate('clu', pos, phrase, cluster_key, geoname_ids)

      clusters[cluster_key] = anchors

    return clusters

  def _find_anchor(self, toponym, geoname):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    if len(hierarchy) == 1:
      return None

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        return geoname

      if len(children) == 1:
        child = children[0]
        if child.is_city:
            return child
        geoname = child
        continue

      return None


class TreeNode:

  def __init__(self, key, parent):
    self.key = key
    self.parent = parent
    self.children = {}  # key: TreeNode
    self.geonames = {}  # phrase: GeoName
    self.positions = {}  # phrase: [pos]

  def __repr__(self):
    return self.key

  def get(self, key_path, create):
    if len(key_path) == 0:
      return self
    key = key_path[0]
    if key not in self.children:
      if create:
        child = TreeNode(key, self)
        self.children[key] = child
      else:
        return None
    else:
      child = self.children[key]
    return child.get(key_path[1:], create)

  def add(self, phrase, geoname, position):
    if phrase not in self.geonames:
      self.geonames[phrase] = geoname
      self.positions[phrase] = [position]
    else:
      self.positions[phrase].append(position)

  def iter(self):
    node = self
    while node.key != None:
      yield node
      node = node.parent
