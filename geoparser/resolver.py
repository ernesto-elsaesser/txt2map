import os
import re
import json
import pylev
from .model import TreeNode
from .geonames import GeoNamesCache, GeoNamesAPI
from .gazetteer import Gazetteer


class ToponymResolver:

  def __init__(self, gns_cache):
    self.gns_cache = gns_cache
    self.gaz = Gazetteer(gns_cache)

  def resolve(self, doc, max_disam_rounds=5):

    heur_mapping = {}

    for pos, phrase, note, toponym in doc.iter('rec'):
      if note == 'gazetteer':
        default_id = int(self.gaz.defaults[toponym])
      else:
        results = self.gns_cache.search(toponym)
        if len(results) == 0:
          continue
        first = results[0]
        doc.annotate('res', pos, phrase, 'api', first.id)
        default = max(results, key=lambda g: self._sim_pop(toponym, g))
        anc_ids = self._resolve_new_ancestors(default, doc)
        for anc_id in anc_ids: 
          heur_mapping[anc_id] = anc_id
        default_id = default.id

      doc.annotate('res', pos, phrase, 'def', default_id)
      heur_mapping[default_id] = default_id

    (root, leafs) = self._make_tree(doc, 'def')
    unsupported = self._find_unsupported_leafs(leafs)

    changed = True
    rounds = 0
    while changed and rounds < max_disam_rounds:
      rounds += 1
      changed = False

      doc.clear_group('res', 'heur')
      for pos, phrase, _, geoname_id in doc.iter('res', exclude=['api']):
        doc.annotate('res', pos, phrase, 'heur', heur_mapping[geoname_id])
      (root, leafs) = self._make_tree(doc, 'heur')
      unsupported = self._find_unsupported_leafs(leafs)

      for adm1 in unsupported:
        (toponym, old_geoname) = list(adm1.geonames.items())[0]
        new_geoname = self._select_heuristically(toponym, old_geoname, root)
        if new_geoname != None:
          changed = True
          heur_mapping[old_geoname.id] = new_geoname.id

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
    small = [g for g in hierarchy[:-1] if g.population <= 100000]
    found_ids = set()
    for ancestor in small:
      name = ancestor.name
      for match in re.finditer(name, doc.text):
        pos = match.start()
        if pos not in blocked:
          found_ids.add(ancestor.id)
          doc.annotate('rec', pos, name, 'ancestor', name)
          doc.annotate('res', pos, name, 'def', ancestor.id)
    return found_ids

  def _make_tree(self, doc, select_group):
    root = TreeNode(None, None)
    leafs = []
    for pos, phrase, _, geoname_id in doc.iter('res', select=select_group):
      geoname = self.gns_cache.get(geoname_id)
      key_path = self._key_path(geoname)
      node = root.get(key_path, True)
      node.add(phrase, geoname, pos)
      if len(key_path) == 3 and node not in leafs:
        leafs.append(node)
    return (root, leafs)

  def _key_path(self, g):
    cont_name = self.gaz.continent_name(g)
    key_path = [cont_name]
    if g.cc != "-":
      key_path.append(g.cc)
      if g.adm1 != "-" and g.adm1 != "00":
        key_path.append(g.adm1)
    return key_path

  def _find_unsupported_leafs(self, leafs):
    if len(leafs) < 2:
      return []

    unsupported = []
    for node in leafs:
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

  def annotate_clusters(self, doc, group):
    (root, _) = self._make_tree(doc, group)
    anchors = []

    for cont in root.children.values():
      if len(cont.children) == 0:
        anchors += self._annotate_cluster(cont, doc, group)
      for country in cont.children.values():
        if len(country.children) == 0:
          anchors += self._annotate_cluster(country, doc, group)
        for admin1 in country.children.values():
          anchors += self._annotate_cluster(admin1, doc, group)

    return anchors

  def _annotate_cluster(self, leaf, doc, group):
      keys = []
      for node in leaf.iter():
        keys.append(node.key)
      cluster_key = '/'.join(reversed(keys))

      tupels = list(leaf.geonames.items())
      anchor_ids = [g.id for _, g in tupels if g.is_city]
      if len(anchor_ids) == 0:
        (toponym, geoname) = min(tupels, key=lambda t: t[1].population)
        anchor = self._find_anchor(toponym, geoname)
        if anchor != None:
          anchor_ids.append(anchor.id)

      for node in leaf.iter():
        for phrase, pos in node.positions.items():
          doc.annotate('clust', pos, phrase, group, cluster_key)

      return anchor_ids

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

