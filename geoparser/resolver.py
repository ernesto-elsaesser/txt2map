import os
import logging
from .model import ResolvedToponym, ToponymCluster
from .geonames import GeoNamesCache

class ToponymResolver:

  def __init__(self, cache_dir):
    self.gns_cache = GeoNamesCache(cache_dir)

  def resolve(self, toponyms):
    logging.info('resolving toponyms ...')

    recognized_names = [t.name for t in toponyms]
    resolved_toponyms = []
    for toponym in toponyms:
      geonames = self.gns_cache.search(toponym.name)
      if len(geonames) == 0: continue
      resolution = self._choose_heuristically(toponym, geonames, recognized_names)
      resolved_toponyms.append(resolution)
    
    return resolved_toponyms

  def _choose_heuristically(self, toponym, geonames, recognized_names):
    geonames = sorted(geonames, key=lambda c: c.population, reverse=True)
    best = self._make_resolution(toponym, geonames[0], recognized_names)

    # always use default sense for continents and countries
    depth = len(best.hierarchy)
    if depth < 2:
      return best

    # if these is no ontological evidence for the default sense while there is
    # for another candidate, choose the next biggest candidate with max. evidence
    best_evidence = len(best.mentioned_ancestors)
    if best_evidence == 0:
      for geoname in geonames[1:10]:
        res = self._make_resolution(toponym, geoname, recognized_names)
        evidence = len(res.mentioned_ancestors)
        if evidence > best_evidence:
          best = res
          best_evidence = evidence

    if best.geoname.is_city:
      return best

    # if best is no city and among the candidates is a similarly named city
    # of which best is an ancestor, prefer the city candidate 
    # (as OSM data is only requested for cities)
    cities = [g for g in geonames if g.is_city and g.name in toponym.name]
    for geoname in cities[:10]:
      res = self._make_resolution(toponym, geoname, recognized_names)
      hierarchy_ids = [g.id for g in res.hierarchy]
      if best.geoname.id in hierarchy_ids:
        return res
    
    return best

  def _make_resolution(self, toponym, geoname, recognized_names):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    mentioned_ancestors = set()
    for g in hierarchy:
      if g.name in toponym.name or toponym.name in g.name:
        continue
      for r_name in recognized_names:
        if r_name in g.name or g.name in r_name:
          mentioned_ancestors.add(r_name)
    return ResolvedToponym(toponym, geoname, hierarchy, mentioned_ancestors)

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
