import os
import logging
import json
import sqlite3
from osm2geojson import json2geojson
from geoparser import Geoparser, DataLoader, GeoNamesAPI, OverpassAPI, GeoUtil

class Result:

  def __init__(self, geonames, osm_elements):
    self.geonames = geonames
    self.osm_elements = osm_elements
    self.annotations = []


class CorpusEvaluator:

  def __init__(self, accuracy_km):
    self.dist_limit = accuracy_km
    self.parser = Geoparser()
    self.known_geonames = {}
    self.results = {}

  def start_corpus(self, corpus):
    self.corpus = corpus
    self.results[corpus] = {}

  def start_document(self, document, text):
    logging.info('--- %s / %s ---', self.corpus, document)
    self.document = document
    geonames = {}
    osm_elements = {}

    clusters = self.parser.parse(text)
    for cluster in clusters:
      for toponym in cluster.toponyms:
        for position in toponym.positions:
          geoname = toponym.geoname
          geonames[position] = geoname
          self.known_geonames[geoname.id] = geoname
      for match in cluster.local_matches:
        for position in match.positions:
          osm_elements[position] = match.elements

    self.results[self.corpus][document] = Result(geonames, osm_elements)

  def geoname_to_coordinates(self, geoname_id):
    if geoname_id in self.known_geonames:
      geoname = self.known_geonames[geoname_id]
    else:
      geoname = GeoNamesAPI.get_geoname(geoname_id)
      self.known_geonames[geoname.id] = geoname
    return (geoname.lat, geoname.lng)

  def verify_annotation(self, position, name, lat, lng):
    c, d = self.corpus, self.document
    result = self.results[c][d]
    present = False
    correct = False

    if position in result.geonames:
      present = True
      geoname = result.geonames[position]
      geometry = self.get_geoname_geometry(geoname)
      correct = self.test_geometry(lat, lng, geometry)
    elif position in result.osm_elements:
      present = True
      osm_elements = result.osm_elements[position]
      feature_collection = self.get_osm_element_geometries(osm_elements)
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

  def document_report(self, corpus=None, document=None):
    c = corpus or self.corpus
    d = document or self.document
    result = self.results[c][d]
    summary = self.document_summary(corpus=c, document=d)
    report = f'{d}: {summary}\n'
    for pos, name, present, correct in result.annotations:
      if correct: continue
      problem = 'Wrong coordinate' if present else 'Missing annotation'
      report += f'- {problem} for {name} at {pos}\n'
    return report

  def corpus_report(self, corpus=None):
    c = corpus or self.corpus
    results = self.results[c]
    report = ''
    for d in results:
      report += self.document_report(corpus=c, document=d)
    corpus_summary = self.corpus_summary(corpus=c)
    report += 'Overall: ' + corpus_summary
    return report

  # --- PRIVATE ---

  def get_geoname_geometry(self, geoname):
    dirname = os.path.dirname(__file__)
    db = sqlite3.connect(dirname + '/shapes.db')
    cursor = db.cursor()
    cursor.execute(
        'SELECT geojson FROM shapes WHERE geoname_id = ?', (geoname.id, ))
    row = cursor.fetchone()
    db.close()
    if row == None:
      return GeoUtil.make_point(geoname.lat, geoname.lng)
    return json.loads(row[0])

  def get_osm_element_geometries(self, osm_elements):
    json_response = OverpassAPI.load_geometries(osm_elements)
    return json2geojson(json_response)

  def test_features(self, lat, lng, feature_collection):
    for feature in feature_collection['features']:
      geometry = feature['geometry']
      if self.test_geometry(lat, lng, geometry):
        return True
    return False

  def test_geometry(self, lat, lng, geometry):
    return GeoUtil.geometry_within_radius(lat, lng, geometry, self.dist_limit)

  def summary(self, annotations):
    total = len(annotations)
    if total == 0:
      return 'no annotations'
    present = [a for a in annotations if a[2]]
    correct = [a for a in annotations if a[3]]
    rel_present = int((len(present)/total) * 100)
    rel_correct = int((len(correct)/total) * 100)
    return f'{total} annotations, {rel_present}% recognized, {rel_correct}% resolved'
