import os
import re
import json
import pylev
from .document import Document
from .geonames import GeoNamesCache, GeoNamesAPI
from .gazetteer import Gazetteer


class ToponymResolver:

  def __init__(self, gns_cache):
    self.gns_cache = gns_cache
    self.gaz = Gazetteer(gns_cache)

  def resolve(self, doc, keep_defaults, max_disam_rounds=5):

    heur_mapping = {}

    for a in doc.get('rec'):
      if a.group == 'gaz':
        default_id = self.gaz.defaults[a.data]
      else:
        results = self.gns_cache.search(a.phrase)
        if len(results) == 0:
          continue
        first = results[0]
        doc.annotate('res', a.pos, a.phrase, 'api', first.id)
        default = max(results, key=lambda g: self._sim_pop(a.phrase, g))
        anc_ids = self._resolve_new_ancestors(default, doc)
        for anc_id in anc_ids: 
          heur_mapping[anc_id] = anc_id
        default_id = default.id

      doc.annotate('res', a.pos, a.phrase, 'def', default_id)
      doc.annotate('res', a.pos, a.phrase, 'sel', default_id)

    changed = not keep_defaults
    rounds = 0
    while changed and rounds < max_disam_rounds:
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

  def _sim_pop(self, toponym, geoname):
    target = toponym.lower()
    name = geoname.name.lower()
    if name == target:
      factor = 1.0
    elif self._is_acro(target, name):
      factor = 1.0
    else:
      dist = pylev.levenshtein(target, name)
      factor = 0.8 ** dist
    return geoname.population * factor

  def _resolve_new_ancestors(self, geoname, doc):
    blocked = doc.annotated_positions('rec')
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    not_gaz = [g for g in hierarchy[:-1] if g.population <= Gazetteer.pop_limit]
    found_ids = set()
    for ancestor in not_gaz:
      name = ancestor.name
      for match in re.finditer(name, doc.text):
        pos = match.start()
        if pos not in blocked:
          found_ids.add(ancestor.id)
          doc.annotate('rec', pos, name, 'ancestor', name)
          doc.annotate('res', pos, name, 'def', ancestor.id)
          doc.annotate('res', pos, name, 'sel', ancestor.id)
    return found_ids

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
      mentions = node.branch_mentions()
      if sum(mentions) > 2 or mentions[0] > 1:
        continue # multiple support or siblings
      if mentions[2] == 1 and len(node.parent.parent.children) == 1:
        continue # exclusive continent
      if mentions[1] == 1 and len(node.parent.children) == 1:
        continue # exclusive country
      unsupported.append(node)

    return unsupported

  def _select_heuristically(self, toponym, current, root):

    options = self.gns_cache.search(toponym)

    if len(options) == 1:
      assert current.id == options[0].id
      return None

    sorted_options = sorted(options, key=lambda g: -self._sim_pop(toponym, g))
    cur_hierarchy = self.gns_cache.get_hierarchy(current.id)
    max_depth = len(cur_hierarchy) + 2

    for g in sorted_options[:10]:

      key_path = self._key_path(g)
      node = root.get(key_path, False)

      if node == None or toponym in node.geonames:
        continue

      hierarchy = self.gns_cache.get_hierarchy(g.id)
      depth = len(hierarchy)
      if depth <= max_depth:
        print(f'Chose {g} over {current} for {toponym}')
        return g

    return None

  def _is_acro(self, abbrev, full):

    if '.' not in abbrev:
      return False

    parts = abbrev.split('.')
    words = full.split(' ')

    widx = 0
    for part in parts:
      trimmed = part.strip()
      if trimmed == '':
        continue
      if widx == len(words):
        return False
      if not words[widx].startswith(part):
        return False
      widx += 1

    return widx == len(words)

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

      cluster_key = f'cl{idx}'
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

  def mentions(self):
    return sum(len(ps) for ps in self.positions.values())

  def branch_mentions(self):
    return [n.mentions() for n in self.iter()]
