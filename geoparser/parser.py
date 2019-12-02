import logging
import os
import spacy
from .model import Toponym
from .loader import DataLoader
from .resolver import ToponymResolver
from .matcher import OSMNameMatcher


class Geoparser:

  def __init__(self, local_search_distance_km=15):
    self.nlp = spacy.load('en_core_web_sm', disable=['parser'])
    self.loader = DataLoader()
    self.resolver = ToponymResolver(self.loader)
    self.local_dist = local_search_distance_km

  def parse(self, text):

    doc = self.nlp(text)
    toponyms = self.get_toponyms(doc)
    anchors = self.get_anchors(doc)

    toponym_str = ', '.join(map(lambda t: t.name, toponyms))
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

    sorted_clusters = self.sort_based_on_confidence(clusters)
    logging.info('finished.')
    
    return sorted_clusters

  def get_toponyms(self, doc):
    toponyms = {}
    for ent in doc.ents:
      if ent.label_ not in ['GPE', 'LOC']:
        continue
      name = ent.text
      pos = ent.start_char
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
        pos += 4
      if name not in toponyms:
        toponyms[name] = Toponym(name, [pos])
      else:
        toponyms[name].positions.append(pos)
    return toponyms.values()

  def get_anchors(self, doc):
    anchors = []
    for token in doc:
      if token.pos_ == 'PROPN' and token.text[0].isupper():
        anchors.append((token.idx, token.idx + len(token)))
    return anchors

  def sort_based_on_confidence(self, clusters):

    if len(clusters) == 0:
      return clusters

    if len(clusters) == 1:
      clusters[0].confidence = 1.0
      return clusters

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

    return sorted(clusters, key=lambda c: c.confidence, reverse=True)
