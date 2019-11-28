import os
import logging
from .model import ToponymCluster

class ToponymResolver:

  @staticmethod
  def resolve(toponyms):
    logging.info('disambiguating toponyms ...')

    for toponym in toponyms:
      candidates = sorted(toponym.candidates, key=lambda c: c.population(), reverse=True)
      if len(candidates) == 0:
        continue
      best = candidates[0]
      max_mentions = max(map(lambda c: c.mentions, candidates))
      if best.mentions < max_mentions:
        for c in candidates:
          if c.mentions == max_mentions:
            best = c
            break
      if not best.geoname.is_city:
        city_candidates = [c for c in candidates if c.geoname.is_city]
        for c in city_candidates:
          hierarchy_ids = [g.id for g in c.hierarchy]
          if best.geoname.id in hierarchy_ids:
            best = c
            break
      toponym.selected = best

  @staticmethod
  def cluster(toponyms):
    logging.info('clustering toponyms ...')

    resolved = [t for t in toponyms if t.selected != None]
    seeds = list(sorted(resolved, key=lambda t: t.selected.population(), reverse=True))

    clusters = []
    bound_names = set()

    while len(seeds) > 0:
      seed = seeds.pop()
      bound_names.add(seed.name)

      # find all matches in the same ADM1 area
      connected = [seed]
      hierarchy_ids = [g.id for g in seed.selected.hierarchy]
      g1 = seed.selected.geoname
      for toponym in resolved:
        if toponym.name in bound_names:
          continue
        g2 = toponym.selected.geoname
        if g1.cc == g2.cc != '-' and g1.adm1 == g2.adm1 != '-':
          connected.append(toponym)
          bound_names.add(toponym.name)
          seeds.remove(toponym)
        elif g2.id in hierarchy_ids:
          connected.append(toponym)
          if toponym in seeds:
            seeds.remove(toponym)

      cities = [t for t in connected if t.selected.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda c: c.selected.population())
      else:
        anchor = min(connected, key=lambda c: c.selected.population())

      cluster = ToponymCluster(connected, cities, anchor)
      clusters.append(cluster)

    return sorted(clusters, key=lambda c: c.mentions, reverse=True)
