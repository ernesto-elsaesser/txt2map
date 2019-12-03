import os
import logging
import math
from .model import ResolvedToponym, ToponymCluster
from .geonames import GeoNamesCache

class ToponymResolver:

  def __init__(self, cache_dir):
    self.gns_cache = GeoNamesCache(cache_dir)

  def resolve(self, toponyms):
    all_names = set(toponyms.values())
    toponym_str = ', '.join(all_names)
    logging.info('global entities: %s', toponym_str)
    logging.info('resolving ...')

    search_results = {}
    selected = {}
    for name in all_names:
      geonames = self.gns_cache.search(name)
      search_results[name] = geonames
      if len(geonames) > 0:
        selected[name] = max(geonames, key=lambda g: g.population)

    changed = True
    rounds = 0
    while changed and rounds < 5:
      rounds += 1
      (selected, changed) = self._select_with_context(selected, toponyms, search_results)
    
    resolved_toponyms = []
    for name, geoname in selected.items():
      positions = [p for p, n in toponyms.items() if n == name]
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      resolved = ResolvedToponym(name, positions, hierarchy)
      resolved_toponyms.append(resolved)

    return resolved_toponyms

  def _select_with_context(self, selected, toponyms, search_results_for_name):
    sorted_positions = list(sorted(toponyms.keys()))
    selected_with_context = {}
    changed = False
    for name in selected:
      first = min(p for p, n in toponyms.items() if n == name)
      context = []
      for pos in sorted_positions:
        context_name = toponyms[pos]
        if context_name != name and context_name in selected:
          context.append(selected[context_name])
        if pos > first:
          break  # include one behind first
      search_results = search_results_for_name[name]
      geoname = self._chose_heuristically(name, search_results, context)
      if geoname.id != selected[name].id:
        changed = True
      selected_with_context[name] = geoname

    return (selected_with_context, changed)

  def _chose_heuristically(self, name, search_results, context):

    sorted_results = sorted(search_results, key=lambda c: c.population, reverse=True)
    options = sorted_results[:7] + search_results[:3]
    
    chosen_hierarchy = None
    chosen_geoname = None
    highscore = -10
    for geoname in options:
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      score = self._score(geoname, hierarchy, context)
      if score > highscore:
        chosen_hierarchy = hierarchy
        chosen_geoname = geoname
        highscore = score

    if chosen_geoname.is_city:
      return chosen_geoname

    # if best is no city and among the candidates is a similarly named city
    # of which best is an ancestor, prefer the city candidate 
    # (as OSM data is only requested for cities)
    cities = [g for g in sorted_results if g.is_city and g.name in name]
    min_depth = len(chosen_hierarchy)
    max_depth = min_depth + 3
    for geoname in cities[:10]:
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      depth = len(hierarchy)
      hierarchy_ids = [g.id for g in hierarchy]
      if min_depth < depth < max_depth and chosen_geoname.id in hierarchy_ids:
        chosen_geoname = geoname
        break
    
    return chosen_geoname

  def _score(self, geoname, hierarchy, context):
    score = 0
    pop = geoname.population
    if pop == 0: pop = 1
    log_pop = int(math.log10(pop))
    score += (log_pop - 3)

    prev_ids = set(g.id for g in context[:-3])
    close_ids = set(g.id for g in context[-3:])
    regions = set(g.region() for g in context if g.adm1 != '-')

    for geoname in hierarchy[:-1]:
      if geoname.id in prev_ids:
        score += 0.5
      if geoname.region() in regions:
        score += 1.0
      if geoname.id in close_ids:
        score += 1.5

    return score

  def cluster(self, resolved_toponyms):
    logging.info('clustering toponyms ...')

    seeds = list(sorted(resolved_toponyms, 
            key=lambda t: t.geoname.population, reverse=True))

    clusters = []
    bound_names = set()

    while len(seeds) > 0:
      seed = seeds.pop()
      bound_names.add(seed.name)

      # find all matches in the same ADM1 area
      connected = [seed]
      hierarchy_ids = [g.id for g in seed.hierarchy]
      g1 = seed.geoname
      for toponym in resolved_toponyms:
        if toponym.name in bound_names:
          continue
        g2 = toponym.geoname
        if g1.cc == g2.cc != '-' and g1.adm1 == g2.adm1 != '-':
          connected.append(toponym)
          bound_names.add(toponym.name)
          seeds.remove(toponym)
        elif g2.id in hierarchy_ids:
          connected.append(toponym)
          if toponym in seeds:
            seeds.remove(toponym)

      cities = [t for t in connected if t.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda c: c.geoname.population)
      else:
        anchor = min(connected, key=lambda c: c.geoname.population)

      cluster = ToponymCluster(connected, cities, anchor)
      clusters.append(cluster)

    return sorted(clusters, key=lambda c: c.mentions(), reverse=True)
