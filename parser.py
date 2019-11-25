import logging
import spacy
import geonames
import osm


class Geoparser:

  def __init__(self):
    self.nlp = spacy.load('en_core_web_sm', disable=['parser'])
    self.gn_matcher = geonames.GeoNamesMatcher()

  def parse(self, text):

    doc = self.nlp(text)
    entity_names = self.get_entity_names(doc)
    anchors = self.get_anchors(doc)

    entity_str = ', '.join(entity_names.keys())
    logging.info('global entities: %s', entity_str)
    clusters = self.gn_matcher.generate_clusters(entity_names)

    usable_clusters = [c for c in clusters if c.city_count > 0]
    for cluster in usable_clusters:

      logging.info('selected cluster: %s', cluster)
      osm_matcher = osm.OSMMatcher()
      osm_matcher.load_name_database(cluster)
      cluster.local_matches = osm_matcher.find_names(text, anchors)

      matches_str = ', '.join(m.name for m in cluster.local_matches)
      logging.info('matches: %s', matches_str)

    sorted_clusters = self.sort_based_on_confidence(clusters)
    logging.info('finished.')
    
    return sorted_clusters

  def get_entity_names(self, doc):
    entity_names = {}
    for ent in doc.ents:
      if ent.label_ not in ['GPE', 'LOC', 'NORP'] or not ent.text[0].isupper():
        continue
      name = ent.text.replace('the ', '').replace('The ', '')
      positions = [] if name not in entity_names else entity_names[name]
      positions.append(ent.start_char)
      entity_names[name] = positions
    return entity_names

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

    most_gn_matches = max(clusters, key=lambda c: c.size)
    most_gn_matches.confidence += 0.4

    most_osm_matches = max(clusters, key=lambda c: len(c.local_matches))
    if len(most_osm_matches.local_matches) > 0:
      most_osm_matches.confidence += 0.3

    biggest_population = max(clusters, key=lambda c: c.population())
    biggest_population.confidence += 0.1

    for cluster in clusters:
      if cluster.city_count > 1:
        cluster.confidence += 0.2
      if len(cluster.local_matches) > 1 and cluster is not most_osm_matches:
        cluster.confidence += 0.2

    return sorted(clusters, key=lambda c: c.confidence, reverse=True)
