import logging
import os
from .recognizer import ToponymRecognizer
from .resolver import ToponymResolver
from .loader import DataLoader
from .matcher import OSMNameMatcher


class Geoparser:

  def __init__(self, local_search_distance_km=15, small_nlp_model=False):
    self.recognizer = ToponymRecognizer(small_nlp_model)
    self.loader = DataLoader()
    self.resolver = ToponymResolver(self.loader)
    self.local_dist = local_search_distance_km

  def parse(self, text):

    (toponyms, anchors) = self.recognizer.parse(text)

    toponym_str = ', '.join(t.name for t in toponyms)
    logging.info('global entities: %s', toponym_str)

    resolved = self.resolver.resolve(toponyms)
    clusters = self.resolver.cluster(resolved)

    for cluster in clusters:
      if len(cluster.cities) == 0: continue

      logging.info('selected cluster: %s', cluster)

      osm_db = self.loader.load_osm_database(cluster, self.local_dist)
      cluster.local_matches = OSMNameMatcher.find_names(text, anchors, osm_db)

      matches_str = ', '.join(m.name for m in cluster.local_matches)
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
