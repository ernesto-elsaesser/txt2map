import os
import datetime
import logging
import geojson
import geojson_utils
from osm2geojson import json2geojson
from geoparser import Geoparser, GeoNamesAPI, OverpassAPI

class CorpusEvaluator:

  def __init__(self, dist_limit_km):
    self.parser = Geoparser()
    self.dist_limit = dist_limit_km * 1000
    self.geoname_cache = {}

  def start_corpus(self, corpus_name):
    now = datetime.datetime.now()
    out_path = f'eval-{corpus_name}-{now.date()}.txt'
    self.out = open(out_path, mode='w', encoding='utf-8')
    self.log_line(f'Starting corpus {corpus_name}')
    self.doc_count = 0
    self.total_tests = 0
    self.tests_passed = 0

  def start_document(self, document_id, text):
    self.log_line(f'Starting document {document_id}')
    self.doc_id = document_id
    self.doc_total_tests = 0
    self.doc_tests_passed = 0
    self.errors = []
    self.gn_anns = {}
    self.osm_anns = {}

    clusters = self.parser.parse(text)
    for cluster in clusters:
      for toponym in cluster.toponyms:
        for position in toponym.positions:
          geoname = toponym.selected.geoname
          self.gn_anns[position] = geoname
          self.geoname_cache[geoname.id] = geoname
      for match in cluster.local_matches:
        for position in match.positions:
          self.osm_anns[position] = match.elements

  def geoname_to_coordinates(self, geoname_id):
    if geoname_id in self.geoname_cache:
      geoname = self.geoname_cache[geoname_id]
    else:
      geoname = GeoNamesAPI.get_geoname(geoname_id)
      self.geoname_cache[geoname_id] = geoname
    return (geoname.lat, geoname.lng)

  def test_gold_coordinates(self, position, name, target_lat, target_lng):
    self.doc_total_tests += 1
    target_point = self.make_point(target_lat, target_lng)

    if position in self.gn_anns:
      geoname = self.gn_anns[position]
      shape = GeoNamesAPI.get_shape(geoname.id)
      if shape == None:
        shape = self.make_point(geoname.lat, geoname.lng)
      passed = self.test_shape(target_point, shape)

    elif position in self.osm_anns:
      osm_elements = self.osm_anns[position]
      json_response = OverpassAPI.load_geometries(osm_elements)
      feature_collection = json2geojson(json_response)
      passed = self.test_features(target_point, feature_collection)

    else:
      self.log_line(f'Missing annotation for {name} at {position}')
      return

    if passed:
      self.doc_tests_passed += 1
    else:
      self.log_line(f'Bad coordinate for {name} at {position}')

  def test_features(self, target_point, feature_collection):
    for feature in feature_collection['features']:
      shape = feature['geometry']
      if self.test_shape(target_point, shape):
        return True
    return False

  def test_shape(self, target_point, shape):
    t = shape['type']
    if t == 'Point':
      distance = geojson_utils.point_distance(target_point, shape)
      return distance < self.dist_limit
    elif t == 'Polygon':
      return geojson_utils.point_in_polygon(target_point, shape)
    elif t == 'MultiPolygon':
      return geojson_utils.point_in_multipolygon(target_point, shape)
    else:
      self.log_line(f'Unexpected shape type: {t}')
      return False

  def make_point(self, lat, lng):
    return geojson.geometry.Point(coordinates=[float(lng), float(lat)])

  def make_linestring(self, coords):
    return geojson.geometry.LineString(coordinates=coords)

  def finish_document(self):
    prefix = f'Finished document'
    self.log_score(prefix, self.doc_total_tests, self.doc_tests_passed)
    self.total_tests += self.doc_total_tests
    self.tests_passed += self.doc_tests_passed
    self.doc_count += 1

  def finish_corpus(self):
    prefix = f'Finished corpus with {self.doc_count} documents'
    self.log_score(prefix, self.total_tests, self.tests_passed)
    self.out.close()

  def log_score(self, prefix, total, passed):
    percentage = 100.0 if total == 0 else passed/total
    self.log_line(f'{prefix}: {passed}/{total} ({percentage:.1f}%)')

  def log_line(self, line):
    logging.info(line)
    now = datetime.datetime.now()
    self.out.write(f'{now.time()} {line} \n')
