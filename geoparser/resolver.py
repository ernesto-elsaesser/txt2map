import os
import logging
import math
import json
import csv
import sqlite3
import re
import pylev
from .model import Candidate, ResolutionSet, ToponymCluster
from .geonames import GeoNamesCache

class ToponymResolver:

  def __init__(self, cache_dir):
    self.gns_cache = GeoNamesCache(cache_dir)

    dirname = os.path.dirname(__file__)
    top_level_file = dirname + '/top-level.json'
    with open(top_level_file, 'r') as f:
      json_dict = f.read()
    self.top_level = json.loads(json_dict)

    self.demonyms = {}
    demonyms_file = dirname + '/demonyms.csv'
    with open(demonyms_file, 'r') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        toponym = row[0]
        demos = row[1].split(',')
        for demonym in demos:
          self.demonyms[demonym] = toponym

  def resolve(self, doc):
    logging.info('resolving ...')

    all_toponyms = doc.toponyms()
    all_sets = []
    ambiguous_sets = []
    for name in all_toponyms:
      rs = self._create_resolution_set(name, doc)
      if rs == None:
        continue
      all_sets.append(rs)
      if len(rs.candidates) == 1:
        continue
      ambiguous_sets.append(rs)
      all_sets += self._scan_for_ancestors(rs, doc, all_toponyms)

    changed = True
    rounds = 0
    while changed and rounds < 3:
      rounds += 1
      selected = {}
      for res_set in all_sets:
        selected[res_set.name] = res_set.selected().geoname
      changed = False
      for res_set in ambiguous_sets:
        changed = self._select_heuristically(res_set, selected, doc) or changed

    return all_sets

  def _create_resolution_set(self, name, doc):
    positions = doc.positions(name)

    if name in self.top_level:
      default = self.gns_cache.get(self.top_level[name])
      geonames = [default]
    elif name in self.demonyms:
      toponym = self.demonyms[name]
      default = self.gns_cache.get(self.top_level[toponym])
      geonames = [default]
    else:
      search_results = self.gns_cache.search(name)
      if len(search_results) == 0:
        return None
      first_result = search_results[0]
      sorted_results = sorted(
          search_results[1:], key=lambda c: c.population, reverse=True)
      geonames = sorted_results[:9]
      if self._similar(first_result.name, name):
        geonames.insert(0, first_result)
      else:
        geonames.append(first_result)

    candidates = []
    for geoname in geonames:
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      candidate = Candidate(hierarchy)
      candidates.append(candidate)

    return ResolutionSet(name, positions, candidates)

  def _scan_for_ancestors(self, res_set, doc, known_toponyms):
    candidates = {}
    for candidate in res_set.candidates:
      for a in candidate.ancestors:
        if a.name in known_toponyms:
          continue
        found = False
        for match in re.finditer(a.name, doc.text):
          found = doc.add_toponym(a.name, match.start()) or found
        if found:
          hierarchy = self.gns_cache.get_hierarchy(a.id)
          candidate = Candidate(hierarchy)
          if a.name in candidates:
            candidates[a.name].append(candidate)
          else:
            candidates[a.name] = [candidate]

    new_sets = []
    for name, geonames in candidates.items():
      positions = doc.positions(name)
      rs = ResolutionSet(name, positions, geonames)
      new_sets.append(rs)

    return new_sets

  def _select_heuristically(self, ambiguous_set, selected, doc):
    name = ambiguous_set.name
    present_ids = set()
    regions = set()
    for n, g in selected.items():
      if n == name: continue
      present_ids.add(g.id)
      if g.adm1 != '-':
        regions.add(g.region())

    first_pos = doc.first(name)
    close_names = set(doc.toponyms_in_window(first_pos - 150, first_pos + 50))
    close_names.remove(name)
    close_ids = set(selected[n].id for n in close_names if n in selected)

    sel_candidate = ambiguous_set.selected()
    sel_idx = ambiguous_set.selected_idx
    most_evidence = self._evidence(name, sel_candidate,
                                   close_ids, regions, present_ids)

    treshold = 1.0
    for idx, candidate in enumerate(ambiguous_set.candidates):
      if idx == sel_idx:
        continue
      evidence = self._evidence(name, candidate,
                             close_ids, regions, present_ids)
      if evidence > most_evidence + treshold:
        logging.info(f'chose {candidate} over {sel_candidate} for {name}')
        ambiguous_set.selected_idx = idx
        most_evidence = evidence

  def _evidence(self, name, candidate, close_ids, regions, present_ids):

    score = 4 / len(candidate.hierarchy)

    c_name = candidate.geoname.name
    if c_name not in name and not self._acronym(c_name) == name:
      dist = pylev.levenshtein(name, c_name)
      score -= (dist ** 1.5) / 10

    for ancestor in candidate.ancestors:
      if ancestor.id in close_ids:
        score += 1.5
      elif ancestor.region() in regions:
        score += 1.0
      elif ancestor.id in present_ids:
        score += 0.5

    return score

  def _acronym(self, name):
    parts = name.split(' ')
    return ''.join(p[0] for p in parts if len(p) > 0)

  def _similar(self, name1, name2):
    return pylev.levenshtein(name1, name2) < 2

  def cluster(self, resolution_sets):
    logging.info('clustering toponyms ...')

    seeds = list(sorted(resolution_sets,
            key=lambda rs: rs.population(), reverse=True))

    clusters = []
    bound_names = set()

    while len(seeds) > 0:
      seed = seeds.pop()
      bound_names.add(seed.name)

      # find all matches in the same ADM1 area
      connected = [seed]
      hierarchy_ids = [g.id for g in seed.hierarchy()]
      g1 = seed.geoname()
      for rs in resolution_sets:
        if rs.name in bound_names:
          continue
        g2 = rs.geoname()
        if g1.cc == g2.cc != '-' and g1.adm1 == g2.adm1 != '-':
          connected.append(rs)
          if rs in seeds:
            bound_names.add(rs.name)
            seeds.remove(rs)
        elif g2.id in hierarchy_ids:
          connected.append(rs)
          if rs in seeds:
            seeds.remove(rs)

      city_sets = [rs for rs in connected if rs.geoname().is_city]

      if len(city_sets) > 0:
        anchor = max(city_sets, key=lambda c: c.population())
        local_context = [rs.geoname() for rs in city_sets]
      else:
        anchor = min(connected, key=lambda c: c.population())
        local_context = self._find_local_context(anchor)

      cluster = ToponymCluster(connected, anchor, local_context)
      clusters.append(cluster)

    return sorted(clusters, key=lambda c: c.mentions(), reverse=True)

  def _find_local_context(self, res_set):
    hierarchy = res_set.hierarchy()
    geoname = res_set.geoname()
    name = res_set.name

    if len(hierarchy) == 1 or geoname.fcl != 'A':
      return []

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        logging.info(f'using {geoname} as local context for {name}')
        return [geoname]

      else:
        children = sorted(children, key=lambda g: g.population, reverse=True)
        for child in children:
          if child.name in name or name in child.name:
            if child.is_city:
              logging.info(f'using {child} as local context for {name}')
              return [child]
            geoname = child
            continue

      return []
