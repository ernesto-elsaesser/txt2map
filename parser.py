import logging
import spacy
import geonames
import osm


class Geoparser:

  max_clusters = 3

  def __init__(self):
    self.nlp = spacy.load("data/spacy-model")
    self.geonames = geonames.GeoNamesClient()

  def parse(self, text):

    doc = self.nlp(text)
    entity_names = self.get_entity_names(doc)
    anchors = self.get_anchors(doc)

    entity_str = ', '.join(entity_names.keys())
    logging.info('global entities: %s', entity_str)
    clusters = self.geonames.generate_clusters(entity_names, self.max_clusters)

    for cluster in clusters:
      logging.info('selected cluster: %s', cluster.description())
      osm_client = osm.OverpassClient()
      osm_client.load_name_database(cluster)
      cluster.matches = osm_client.find_names(text, anchors)

      matches_str = ', '.join(m.name for m in cluster.matches)
      logging.info('matches: %s', matches_str)

    logging.info('finished.')
    return self.geonames.calculate_confidences(clusters)

  def get_entity_names(self, doc):
    entity_names = {}
    for ent in doc.ents:
      if ent.label_ not in ['GPE', 'LOC', 'NORP'] or not ent.text[0].isupper():
        continue
      name = ent.text.replace('the ', '').replace('The ', '')
      count = 1 if name not in entity_names else entity_names[name] + 1
      entity_names[name] = count
    return entity_names

  def get_anchors(self, doc):
    anchors = []
    for token in doc:
      if token.pos_ == 'PROPN' and token.text[0].isupper():
        anchors.append((token.idx, token.idx + len(token)))
    return anchors

