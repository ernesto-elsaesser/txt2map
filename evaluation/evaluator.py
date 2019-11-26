import os
import datetime
import logging
from geopy.distance import distance
from geoparser import Geoparser, GeoNamesAPI, OverpassAPI

class CorpusEvaluator:

  def __init__(self, dist_limit):
    self.parser = Geoparser()
    self.dist_limit = dist_limit
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
          self.gn_anns[position] = geoname.coordinate
          self.geoname_cache[geoname.id] = geoname.coordinate
      for match in cluster.local_matches:
        for position in match.positions:
          self.osm_anns[position] = match.elements

  def geoname_to_coordinate(self, geoname_id):
    if geoname_id in self.geoname_cache:
      return self.geoname_cache[geoname_id]
    geoname = GeoNamesAPI.get_geoname(geoname_id)
    self.geoname_cache[geoname_id] = geoname.coordinate
    return geoname.coordinate

  def test_gold_coordinate(self, position, name, target_coord):
    self.doc_total_tests += 1

    if position in self.gn_anns:
      coords = [self.gn_anns[position]]

    elif position in self.osm_anns:
      osm_elements = self.osm_anns[position]
      csv_reader = OverpassAPI.load_all_coordinates(osm_elements)
      coords = list(map(lambda r: (float(r[0]), float(r[1])), csv_reader))
      if len(coords) == 0:
        self.log_line(f'No coordinates from OSM elements for {name}: {osm_elements}')
        return

    else:
      self.log_line(f'Missing annotation for {name} at {position}')
      return

    dist = self.coords_in_range(coords, target_coord)
    if dist < self.dist_limit:
      self.doc_tests_passed += 1
    else:
      self.log_line(f'Bad coordinate for {name} at {position} - {dist:.1f} km off')

  def coords_in_range(self, coords, target_coord):
    lat_sum = lng_sum = 0.0
    count = 0
    for lat, lng in coords:
      lat_sum += lat
      lng_sum += lng
      count += 1
    avg_lat = lat_sum / count
    avg_lng = lng_sum / count
    dist = distance((avg_lat, avg_lng), target_coord)
    return dist.km

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
