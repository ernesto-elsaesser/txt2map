import os
import logging
import re
import json
import pylev
from .model import TreeNode, LocalLayer
from .geonames import GeoNamesCache


class ToponymResolver:

  def __init__(self, gns_cache):
    self.gns_cache = gns_cache
    
    dirname = os.path.dirname(__file__)
    continents_file = dirname + '/continents.json'
    with open(continents_file, 'r') as f:
      json_dict = f.read()
    self.continent_map = json.loads(json_dict)

  def resolve(self, doc, max_disam_rounds=5):

    for d in doc.demonyms:
      doc.selected_senses[d] = doc.default_senses[d]

    for t in doc.gaz_toponyms:
      doc.selected_senses[t] = doc.default_senses[t]

    options = {}

    for t in doc.ner_toponyms:
      candidates = self._load_candidates(t, doc)
      if len(candidates) > 0:
        options[t] = candidates

    (root, leafs) = self._make_tree(doc)
    unsupported = self._find_unsupported_leafs(leafs)
    for t in unsupported:
      if t in doc.gaz_toponyms:
        candidates = self._load_candidates(t, doc)
        if len(candidates) > 0:
          options[t] = candidates

    changed = True
    rounds = 0
    while changed and rounds < max_disam_rounds:
      rounds += 1
      changed = False
      for t in unsupported:
        selection = self._select_heuristically(t, doc, root, options[t])
        if selection != doc.selected_senses[t]:
          changed = True
        doc.selected_senses[t] = selection
      (root, leafs) = self._make_tree(doc)

    doc.local_layers = self._extract_local_layers(leafs, doc)

  def _load_candidates(self, toponym, doc):
    candidates = self.gns_cache.search(toponym)

    if len(candidates) == 0:
      return None

    first = candidates[0]
    if toponym in doc.default_senses:
      assert doc.default_senses[toponym].id == first.id

    if len(candidates) == 1:
      if toponym in doc.default_senses:
        assert doc.default_senses[toponym].id == first.id
      else:
        doc.default_senses[toponym] = first
        doc.selected_senses[toponym] = first
      return None

    sorted_by_pos = sorted(candidates, key=lambda g: -g.population)
    largest = sorted_by_pos[0]

    if toponym in doc.default_senses:
      assert doc.default_senses[toponym].id == largest.id
    else:
      self._resolve_new_ancestors(largest, doc)

    doc.default_senses[toponym] = largest
    doc.selected_senses[toponym] = largest
    if first.id != largest.id:
      doc.api_selected_senses[toponym] = first

    return sorted_by_pos[1:]

  def _resolve_new_ancestors(self, geoname, doc):
    known_toponyms = list(doc.gaz_toponyms)
    known_toponyms += list(doc.ner_toponyms)
    known_toponyms += list(doc.anc_toponyms)
    hierarchy = self._hierarchy(geoname, doc)
    small = [g for g in hierarchy[:-1] if g.population >= 100000]
    for ancestor in small:
      toponym = ancestor.name
      overlaps = [t for t in known_toponyms if toponym in t]
      if len(overlaps) > 0:
        continue
      positions = []
      for match in re.finditer(toponym, doc.text):
        positions.append(match.start())
      if len(positions) > 0:
        logging.info(f'Found ancestor {toponym} of {geoname}')
        doc.anc_toponyms[toponym] = positions
        doc.default_senses[toponym] = ancestor
        doc.selected_senses[toponym] = ancestor

  def _make_tree(self, doc):
    root = TreeNode('', None)
    leafs = []
    for t, g in doc.selected_senses.items():
      key_path = []
      if g.is_continent:
        key_path = [g.name]
      else:
        cont_name = self.continent_map[g.cc]
        key_path = [cont_name, g.cc]
        if g.adm1 != '-':
          key_path.append(g.adm1)
      node = root.get(key_path, True)
      positions = doc.positions(t)
      node.add(t, g, positions)
      if len(key_path) == 3 and node not in leafs:
        leafs.append(node)
    return (root, leafs)

  def _find_unsupported_leafs(self, leafs):
    if len(leafs) < 2:
      return []

    unsupported = []
    for node in leafs:
      counts = node.topo_counts()
      if sum(counts) > 2 or counts[0] > 1:
        continue # multiple support or siblings
      if counts[2] == 1 and len(node.parent.parent.children) == 1:
        continue # exclusive continent
      if counts[1] == 1 and len(node.parent.children) == 1:
        continue # exclusive country
      toponym = next(iter(node.toponyms))
      unsupported.append(toponym)

    return unsupported

  def _select_heuristically(self, toponym, doc, root, options):

    selected = doc.default_senses[toponym]
    sel_hierarchy = self._hierarchy(selected, doc)
    max_depth = len(sel_hierarchy) + 2

    for g in options[:10]:
      if g.cc == '-' or g.adm1 == '-':
        continue
      
      cont_name = self.continent_map[g.cc]
      key_path = [cont_name, g.cc, g.adm1]
      node = root.get(key_path, False)

      if node == None or node.key == selected.adm1:
        continue

      hierarchy = self._hierarchy(g, doc)
      depth = len(hierarchy)
      if depth <= max_depth:
        logging.info(f'Chose {g} over {selected} for {toponym}')
        return g

    return None
      
  def _hierarchy(self, geoname, doc):
    if geoname.id in doc.hierarchies:
      return doc.hierarchies[geoname.id]
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    doc.hierarchies[geoname.id] = hierarchy
    return hierarchy

  def _extract_local_layers(self, leafs, doc):
    layers = []
    for node in leafs:
      geonames = list(node.toponyms.values())
      cities = [g for g in geonames if g.is_city]
      anchor_points = cities

      if len(cities) > 0:
        base = max(cities, key=lambda c: c.population)
      else:
        base = min(geonames, key=lambda c: c.population)
      
      base_hierarchy = self._hierarchy(base, doc)

      if len(anchor_points) == 0:
        anchor = self._drill_down(base, base_hierarchy)
        if anchor == None:
          logging.info(f'no anchor point available for {base}')
          continue
        logging.info(f'using {anchor} as anchor point for {base}')
        anchor_points.append(anchor)

      mentions = node.branch_mentions()
      layer = LocalLayer(base, base_hierarchy, node.toponyms, anchor_points, mentions)
      layers.append(layer)

    return layers

  def _drill_down(self, geoname, hierarchy):

    if len(hierarchy) == 1 or geoname.fcl != 'A':
      return None

    name = geoname.name

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        return geoname

      else:
        children = sorted(children, key=lambda g: g.population, reverse=True)
        similar_child = None
        for child in children:
          if child.name in name or name in child.name:
            if child.is_city:
              return child
            similar_child = child
            break

        if similar_child != None:
          geoname = similar_child
          continue

      return []
