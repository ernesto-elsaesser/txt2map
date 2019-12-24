import os
import re
import json
import pylev
from .document import Document
from .geonames import GeoNamesCache, GeoNamesAPI
from .gazetteer import Gazetteer
from .config import Config


class ToponymResolver:

  def __init__(self, gazetteer):
    self.gaz = gazetteer
    self.gns_cache = GeoNamesCache()

  def resolve(self, doc, keep_defaults):
    self.candidates = {}

    for a in doc.get('rec', 'ner'):
      if a.data in self.gaz.defaults:
        continue
      candidates = self._select_candidates(a.phrase)
      if len(candidates) > 0:
        self._resolve_new_ancestors(candidates[0], doc)

    doc.clear_overlaps('rec')

    annotated = []
    for a in doc.get('rec'):
      if a.pos in annotated:
        continue
      annotated.append(a.pos)
      if a.data in self.gaz.defaults:
        default_id = self.gaz.defaults[a.data]
      else:
        candidates = self._select_candidates(a.phrase)
        if len(candidates) == 0:
          continue
        default = candidates[0]
        default_id = default.id

      doc.annotate('res', a.pos, a.phrase, 'def', default_id)
      doc.annotate('res', a.pos, a.phrase, 'sel', default_id)

    changed = not keep_defaults
    rounds = 0
    max_rounds = Config.resol_max_disam_rounds
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
          id_map[old_geoname.id] = new_geoname.id

      for a in doc.get('res', 'sel'):
        if a.data in id_map:
          a.data = id_map[a.data]

  def _select_candidates(self, toponym):
    if toponym in self.candidates:
      return self.candidates[toponym]
    if '.' in toponym:
      prefix = toponym.split('.')[0]
      toponyms = self.gaz.lookup_prefix(prefix)
      geoname_ids = [self.gaz.defaults[t] for t in toponyms]
      cs = [self.gns_cache.get(gid) for gid in geoname_ids]
    else:
      results = self.gns_cache.search(toponym)
      cs = [g for g in results if toponym in g.name]
      if len(cs) == 0:
        cs = [g for g in results if toponym in g.name]
    cs = sorted(cs, key=lambda g: -g.population)
    self.candidates[toponym] = cs
    return cs

  def _resolve_new_ancestors(self, geoname, doc):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    pop_limit = Config.gazetteer_population_limit
    not_gaz = [g for g in hierarchy[:-1] if g.population <= pop_limit]
    for ancestor in not_gaz:
      name = ancestor.name
      if name in geoname.name:
        continue
      for match in re.finditer(name, doc.text):
        doc.annotate('rec', match.start(), name, 'ancestor', name)

  def _make_tree(self, doc):
    root = TreeNode(None, None)
    adm1s = []
    for a in doc.get('res', 'sel'):
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

      if len(g.name) > len(toponym) and g.population == 0:
        continue

      hierarchy = self.gns_cache.get_hierarchy(g.id)
      depth = len(hierarchy)
      if depth <= max_depth:
        print(f'Chose {g} over {current} for {toponym}')
        return g

    return None

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

    if len(hierarchy) == 1 or geoname.fcl != 'A':
      return None

    search_results = self.gns_cache.search(toponym)
    search_ids = set(g.id for g in search_results)

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        return geoname

      else:
        children = sorted(children, key=lambda g: g.population, reverse=True)
        similar_child = None
        for child in children:
          if child.id in search_ids or child.name in geoname.name or geoname.name in child.name:
            if child.is_city:
              return child
            similar_child = child
            break

        if similar_child != None:
          geoname = similar_child
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
