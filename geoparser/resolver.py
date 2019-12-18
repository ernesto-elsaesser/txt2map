import os
import logging
import re
import pylev
from .model import ToponymCluster
from .geonames import GeoNamesCache

class ToponymResolver:

  def __init__(self, gns_cache, doc):
    self.gns_cache = gns_cache
    self.doc = doc
    self.recognized = doc.positions
    self.defaults = doc.geonames
    self.non_defaults = {}
    self.selections = {}
    self.hierarchies = {}

  def resolve(self):
    logging.info('resolving ...')

    # fetch candidates for toponyms not ing gazetteer
    for toponym in self.recognized:
      if toponym not in self.defaults:
        self._fetch_candidates(toponym)

    # fetch hierarchies for selected geonames
    for geoname in self._currently_selected().values():
        self._fetch_hierarchy(geoname)

    # un-default unconnected low-level toponyms
    groups = self._group_by_region()
    unstables = set()
    if len(groups) > 1:
      for toponyms in groups:
        if len(toponyms) == 1:
          unstables.add(toponyms[0])
        elif len(toponyms) == 2:
          for group in groups:
            if group == toponyms: continue
            if toponyms[0] in group:
              unstables.add(toponyms[1])
            if toponyms[1] in group:
              unstables.add(toponyms[0])
    
    for toponym in unstables:
      if toponym not in self.defaults:
        continue
      g = self.defaults[toponym]
      if not g.is_continent and not g.is_country and not g.is_ocean:
        logging.info(f'Considering non-default senses for {toponym}')
        del self.defaults[toponym]
        self._fetch_candidates(toponym)

    # fetch all hierarchies for non-defaults
    for _, candidates in self.non_defaults.items():
      for candidate in candidates:
        self._fetch_hierarchy(candidate)

    # choose best non-defaults
    changed = True
    rounds = 0
    while changed and rounds < 3:
      rounds += 1
      new_selections = {}
      changed = False
      for toponym in self.non_defaults:
        new_selection = self._select_heuristically(toponym)
        if new_selection != self.selections[toponym]:
          changed = True
        new_selections[toponym] = new_selection
      self.selections = new_selections

    # commit choices
    for toponym, geoname in self._currently_selected().items():
      self.doc.resolve(toponym, geoname)

  def _fetch_candidates(self, toponym):
    search_results = self.gns_cache.search(toponym)
    if len(search_results) == 0:
      return

    first_result = search_results[0]
    sorted_results = sorted(
        search_results[1:], key=lambda c: c.population, reverse=True)
    candidates = sorted_results[:9]
    if self._similar(first_result.name, toponym):
      candidates.insert(0, first_result)
    else:
      candidates.insert(1, first_result)

    self.non_defaults[toponym] = candidates
    self.selections[toponym] = 0

    return candidates[0]

  def _fetch_hierarchy(self, geoname):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    self.hierarchies[geoname.id] = hierarchy

    for ancestor in hierarchy[:-1]:
      toponym = ancestor.name
      if ancestor.population >= 50000:
        continue
      overlaps = [t for t in self.recognized if toponym in t]
      if len(overlaps) > 0:
        continue
      positions = []
      for match in re.finditer(toponym, self.doc.text):
        positions.append(match.start())
      if len(positions) > 0:
        logging.info(f'Found {toponym} as ancestor of {geoname}')
        self.doc.recognize(toponym, positions)
        self.doc.resolve(toponym, ancestor)
        self.defaults[toponym] = ancestor

  def _currently_selected(self):
    selected = {}
    for toponym in self.defaults:
      selected[toponym] = self.defaults[toponym]
    for toponym in self.non_defaults:
      selected[toponym] = self.non_defaults[toponym][self.selections[toponym]]
    return selected

  def _group_by_region(self):
    selected = self._currently_selected()
    resolved = list(selected.keys())
    seeds = list(sorted(resolved, key=lambda t: selected[t].population))
    # smallest first to avoid using top levels as seeds

    groups = []
    grouped = set()

    for toponym in seeds:
      if toponym in grouped:
        continue

      (apos, spos) = self._find_ancestors_and_siblings(toponym, selected[toponym])
      ancestors = list(apos.keys())
      siblings = list(spos.keys())
      group = [toponym] + ancestors + siblings

      for t in group:
        grouped.add(t)
      groups.append(group)

    return groups

  def _find_ancestors_and_siblings(self, toponym, geoname):
    region = geoname.region()
    ancestors = self.hierarchies[geoname.id][:-1]
    ancestor_ids = [g.id for g in ancestors]
    ancestors = {}
    siblings = {}
    selected = self._currently_selected()
    for t, g in selected.items():
      if t == toponym:
        continue
      if g.id in ancestor_ids:
        ancestors[t] = self.recognized[t]
      elif g.region() == region:
        siblings[t] = self.recognized[t]
    return (ancestors, siblings)

  def _select_heuristically(self, toponym):
    candidates = self.non_defaults[toponym]
    selection = self.selections[toponym]
    selected = candidates[selection]
    
    most_evidence = self._evidence(toponym, selected)

    new_selection = selection
    treshold = 1.0
    for idx, candidate in enumerate(candidates):
      if idx == selection:
        continue
      evidence = self._evidence(toponym, candidate)
      if evidence > most_evidence + treshold:
        logging.info(f'chose {candidate} over {selected} for {toponym}')
        new_selection = idx
        most_evidence = evidence

    return new_selection

  def _evidence(self, toponym, geoname):
    first = min(self.recognized[toponym])
    name = geoname.name
    acronym = self._acronym(name)
    hierarchy = self.hierarchies[geoname.id]
    (apos, spos) = self._find_ancestors_and_siblings(toponym, geoname)

    score = 4 / len(hierarchy)

    if name not in toponym and not acronym == toponym:
      dist = pylev.levenshtein(toponym, name)
      score -= (dist ** 1.5) / 10

    for positions in apos.values():
      preceeding = min(positions) < first + 50
      score += 1.5 if preceeding else 0.5
    for _ in spos:
      score += 1.0

    return score

  def _acronym(self, name):
    parts = name.split(' ')
    return ''.join(p[0] for p in parts if len(p) > 0)

  def _similar(self, name1, name2):
    return pylev.levenshtein(name1, name2) < 2

  def make_clusters(self):
    logging.info('clustering toponyms ...')

    groups = self._group_by_region()
    selected = self._currently_selected()
    clusters = []

    for toponyms in groups:
      geonames = [selected[t] for t in toponyms]
      cities = [g for g in geonames if g.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda c: c.population)
        local_context = cities
      else:
        anchor = min(geonames, key=lambda c: c.population)
        local_context = self._drill_down(anchor)

      hierarchy = self.hierarchies[anchor.id]
      cluster = ToponymCluster(toponyms, hierarchy, local_context)
      clusters.append(cluster)

    return clusters

  def _drill_down(self, geoname):
    hierarchy = self.hierarchies[geoname.id]

    if len(hierarchy) == 1 or geoname.fcl != 'A':
      return []

    name = geoname.name

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        logging.info(f'using {geoname} as local context')
        return [geoname]

      else:
        children = sorted(children, key=lambda g: g.population, reverse=True)
        similar_child = None
        for child in children:
          if child.name in name or name in child.name:
            if child.is_city:
              logging.info(f'using {child} as local context for {name}')
              return [child]
            similar_child = child
            break

        if similar_child != None:
          geoname = similar_child
          continue

      return []
