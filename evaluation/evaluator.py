import os
import logging
from geojson.geometry import Point
import geojson_utils
from geoparser import Geoparser, DataLoader

class Result:

  def __init__(self, geonames, osm_elements):
    self.geonames = geonames
    self.osm_elements = osm_elements
    self.annotations = []

class CorpusEvaluator:

  def __init__(self, dist_limit_km):
    self.dist_limit = dist_limit_km * 1000
    self.parser = Geoparser()
    self.loader = DataLoader()
    self.results = {}

  def start_corpus(self, corpus):
    self.corpus = corpus
    self.results[corpus] = {}

  def start_document(self, document, text):
    logging.info('--- %s.%s ---', self.corpus, document)
    self.document = document
    geonames = {}
    osm_elements = {}

    clusters = self.parser.parse(text)
    for cluster in clusters:
      for toponym in cluster.toponyms:
        for position in toponym.positions:
          geoname = toponym.selected.geoname
          geonames[position] = geoname
      for match in cluster.local_matches:
        for position in match.positions:
          osm_elements[position] = match.elements

    self.results[self.corpus][document] = Result(geonames, osm_elements)

  def geoname_to_coordinates(self, geoname_id):
    geoname = self.loader.load_geoname_hierarchy(geoname_id)[-1]
    return (geoname.lat, geoname.lng)

  def verify_annotation(self, position, name, lat, lng):
    c, d = self.corpus, self.document
    result = self.results[c][d]
    present = False
    correct = False

    if position in result.geonames:
      present = True
      geoname = result.geonames[position]
      shape = self.loader.get_geoname_shape(geoname)
      correct = self.test_shape(lat, lng, shape)
    elif position in result.osm_elements:
      present = True
      osm_elements = result.osm_elements[position]
      feature_collection = self.loader.load_osm_geometries(osm_elements)
      correct = self.test_features(lat, lng, feature_collection)

    annotation = (position, name, present, correct)
    self.results[c][d].annotations.append(annotation)

  def document_summary(self, corpus=None, document=None):
    c = corpus or self.corpus
    d = document or self.document
    result = self.results[c][d]
    return self.summary(result.annotations)

  def corpus_summary(self, corpus=None):
    c = corpus or self.corpus
    results = self.results[c]
    all_annotations = sum([r.annotations for r in results.values()], [])
    return self.summary(all_annotations)

  def evaluation_report(self, corpus=None):
    c = corpus or self.corpus
    results = self.results[c]

    log = ''
    for document, result in results.items():
      summary = self.document_summary(corpus=c, document=document)
      log += f'{document}: {summary}\n'
      for pos, name, present, correct in result.annotations:
        if correct: continue
        problem = 'Wrong coordinate' if present else 'Missing annotation'
        log += f'- {problem} for {name} at {pos}\n'
    corpus_summary = self.corpus_summary(corpus=c)
    log += '\nOverall: ' + corpus_summary

    return log

  # --- PRIVATE ---

  def test_features(self, lat, lng, feature_collection):
    for feature in feature_collection['features']:
      shape = feature['geometry']
      if self.test_shape(lat, lng, shape):
        return True
    return False

  def test_shape(self, lat, lng, shape):
    t = shape['type']
    target = Point(coordinates=[lng, lat])
    if t == 'Point':
      distance = geojson_utils.point_distance(target, shape)
      return distance < self.dist_limit
    elif t == 'Polygon':
      return geojson_utils.point_in_polygon(target, shape)
    elif t == 'MultiPolygon':
      return geojson_utils.point_in_multipolygon(target, shape)
    else:
      logging.warning(f'Unexpected shape type: {t}')
      return False

  def summary(self, annotations):
    total = len(annotations)
    if total == 0:
      return 'no annotations'
    present = [a for a in annotations if a[2]]
    correct = [a for a in annotations if a[3]]
    rel_present = int((len(present)/total) * 100)
    rel_correct = int((len(correct)/total) * 100)
    return f'{total} annotations, {rel_present}% recgonized, {rel_correct}% resolved'
