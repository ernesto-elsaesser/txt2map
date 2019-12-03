import os
import logging
import math
from .model import ResolvedToponym, ToponymCluster
from .geonames import GeoNamesCache

class ToponymResolver:

  def __init__(self, cache_dir):
    self.gns_cache = GeoNamesCache(cache_dir)

  def resolve(self, toponyms):
    logging.info('resolving toponyms ...')

    resolved_toponyms = []
    for toponym in toponyms:
      geonames = self.gns_cache.search(toponym.name)
      if len(geonames) == 0: continue
      resolution = self._choose_heuristically(toponym, geonames, toponyms)
      resolved_toponyms.append(resolution)
    
    return resolved_toponyms

  def _choose_heuristically(self, toponym, geonames, toponyms):
    sorted_by_size = sorted(geonames, key=lambda c: c.population, reverse=True)

    options = geonames[:3] + sorted_by_size[:7]
    chosen = self._make_resolution(toponym, geonames[0], toponyms)
    best = self._score(chosen)
    for geoname in options:
      res = self._make_resolution(toponym, geoname, toponyms)
      score = self._score(res)
      if score > best:
        chosen = res
        best = score

    if chosen.geoname.is_city:
      return chosen

    # if best is no city and among the candidates is a similarly named city
    # of which best is an ancestor, prefer the city candidate 
    # (as OSM data is only requested for cities)
    cities = [g for g in sorted_by_size if g.is_city and g.name in toponym.name]
    min_depth = chosen.depth
    max_depth = chosen.depth + 3
    for geoname in cities[:10]:
      res = self._make_resolution(toponym, geoname, toponyms)
      hierarchy_ids = [g.id for g in res.hierarchy]
      if min_depth < res.depth < max_depth and chosen.geoname.id in hierarchy_ids:
        return res
    
    return chosen

  def _score(self, resolution):
    score = 0
    p = resolution.geoname.population
    if p > 0:
      score += max(0, math.log10(p) - 5)
    for _, d in resolution.support:
      if 0 <= d < 50: # between or shortly after
        score += 1
      elif d < 0: # before
        score += 1 - (max(-d, 900) / 1000)
    return score

  def _make_resolution(self, toponym, geoname, toponyms):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    hierarchy_names = set(g.name for g in hierarchy)
    redundant_names = set()
    for name in hierarchy_names:
      for other_name in hierarchy_names:
        if name != other_name and name in other_name:
          redundant_names.add(other_name)
    unique_names = hierarchy_names.difference(redundant_names)
    min_pos = min(toponym.positions)
    max_pos = min(toponym.positions)
    support = []
    counted_pos = []
    for name in unique_names:
      for other in toponyms:
        if other.name in name or name in other.name:
          for p in other.positions:
            if p in counted_pos: continue
            if p < min_pos: d = p - min_pos
            elif p > max_pos: d = p - max_pos
            else: d = 0
            support.append((other.name, d))

    return ResolvedToponym(toponym, geoname, hierarchy, support)

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
