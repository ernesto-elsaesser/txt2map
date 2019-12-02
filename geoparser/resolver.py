import os
import logging
from .model import ResolvedToponym, ToponymCluster
from .geonames import GeoNamesAPI
from .loader import DataLoader

class ToponymResolver:

  def __init__(self, loader):
    self.loader = loader

  def resolve(self, toponyms):
    logging.info('resolving toponyms ...')

    toponym_names = [t.name for t in toponyms]
    resolved_toponyms = []
    for t in toponyms:
      geonames = GeoNamesAPI.search(t.name)
      if len(geonames) == 0: continue
      geonames = sorted(geonames, key=lambda c: c.population, reverse=True)
      best = self.resolve_toponym(t, geonames[0], toponym_names)

      # if best is a below country level and has no ontological evidence while
      # another candidates have, choose the next biggest candidate with max. evidence
      depth = len(best.hierarchy)
      best_evidence = len(best.mentioned_ancestors)
      if depth > 2 and best_evidence == 0:
        for geoname in geonames[1:10]:
          res = self.resolve_toponym(t, geoname, toponym_names)
          evidence = len(res.mentioned_ancestors)
          if evidence > best_evidence:
            best = res
            best_evidence = evidence

      # if best is no city and among the candidates is a city of which best is an ancestor,
      # prefer the city candidate (as OSM data is only requested for cities)
      if not best.geoname.is_city:
        cities = [g for g in geonames if g.is_city]
        for geoname in cities[:10]:
          res = self.resolve_toponym(t, geoname, toponym_names)
          hierarchy_ids = [id for id, _ in res.hierarchy]
          if best.geoname.id in hierarchy_ids:
            best = res
            break

      resolved_toponyms.append(best)
    
    return resolved_toponyms

  def resolve_toponym(self, toponym, geoname, toponym_names):
    hierarchy = self.loader.get_hierarchy(geoname.id)
    mentioned_ancestors = set()
    for _, name in hierarchy:
      if name in toponym.name or toponym.name in name:
        continue
      for ancestor_name in toponym_names:
        if ancestor_name in name or name in ancestor_name:
          mentioned_ancestors.add(ancestor_name)
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
      hierarchy_ids = [id for id, _ in seed.hierarchy]
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
