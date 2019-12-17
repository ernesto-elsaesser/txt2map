import logging
import os
from .recognizer import ToponymRecognizer
from .resolver import ToponymResolver
from .geonames import GeoNamesCache
from .osm import OSMLoader


class Geoparser:

  def __init__(self, use_large_model=True, local_search_dist_km=15, cache_dir='cache'):
    if not os.path.exists(cache_dir):
      os.mkdir(cache_dir)
    self.recognizer = ToponymRecognizer(use_large_model)
    self.gns_cache = GeoNamesCache(cache_dir)
    self.search_local = local_search_dist_km > 0
    if self.search_local:
      self.osm_loader = OSMLoader(cache_dir, local_search_dist_km)

  def parse(self, text):
    doc = self.recognizer.parse(text)

    toponym_str = ', '.join(doc.toponyms())
    logging.info('global entities: %s', toponym_str)

    resolver = ToponymResolver(self.gns_cache, doc)
    resolver.resolve()
    clusters = resolver.make_cluster()

    if self.search_local:
      for cluster in clusters:
        if len(cluster.local_context) == 0:
          continue

        logging.info('selected cluster: %s', cluster)
        match_names = self.osm_loader.find_local_matches(cluster, doc)

        matches_str = ', '.join(match_names)
        logging.info('matches: %s', matches_str)

    self.assign_confidences(clusters)
    logging.info('finished.')

    return sorted(clusters, key=lambda c: c.confidence, reverse=True)

  def assign_confidences(self, clusters):

    if len(clusters) == 0:
      return

    if len(clusters) == 1:
      clusters[0].confidence = 1.0
      return

    most_gns_matches = max(clusters, key=lambda c: c.mentions())
    most_gns_matches.confidence += 0.4

    most_osm_matches = max(clusters, key=lambda c: len(c.local_matches))
    if len(most_osm_matches.local_matches) > 0:
      most_osm_matches.confidence += 0.3

    biggest_population = max(clusters, key=lambda c: c.population())
    biggest_population.confidence += 0.1

    for cluster in clusters:
      if cluster.size > 1:
        cluster.confidence += 0.2
      if len(cluster.local_matches) > 1 and cluster is not most_osm_matches:
        cluster.confidence += 0.2
