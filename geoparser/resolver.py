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
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)

      if not geoname.is_city:
        results = search_results[name]
        city_hierarchy = self._find_city_ancestor(hierarchy, results)
        if city_hierarchy != None:
          hierarchy = city_hierarchy

      positions = [p for p, n in toponyms.items() if n == name]
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
    chosen = search_results[0]
    hierarchy = self.gns_cache.get_hierarchy(chosen.id)
    if chosen.name == name and len(hierarchy) < 3:
      return chosen

    sorted_by_size = sorted(search_results, key=lambda c: c.population, reverse=True)
    chosen = None
    highscore = -10
    for geoname in sorted_by_size[:10]:
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      score = self._score(name, geoname, hierarchy, context)
      if score > highscore:
        chosen = geoname
        highscore = score

    return chosen

  def _score(self, name, geoname, hierarchy, context):
    score = 0
    depth = len(hierarchy)
    pop = geoname.population
    if pop == 0: pop = 1
    score += math.log10(pop) - depth

    prev_ids = set(g.id for g in context[:-3])
    close_ids = set(g.id for g in context[-3:])
    regions = set(g.region() for g in context if g.adm1 != '-')

    for geoname in hierarchy[:-1]:
      if geoname.id in close_ids:
        score += 1.5
      elif geoname.region() in regions:
        score += 1.0
      elif geoname.id in prev_ids:
        score += 0.5

    return score

  def _find_city_ancestor(self, hierarchy, search_results):
    base = hierarchy[-1]
    cities = [g for g in search_results if g.is_city and g.name in base.name]
    cities = sorted(cities, key=lambda c: c.population, reverse=True)
    min_depth = len(hierarchy)
    max_depth = min_depth + 3

    for geoname in cities[:10]:
      city_hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      depth = len(city_hierarchy)
      hierarchy_ids = [g.id for g in city_hierarchy]
      if min_depth < depth < max_depth and base.id in hierarchy_ids:
        return city_hierarchy

    return None

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
