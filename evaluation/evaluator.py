import os
import datetime
import logging
from geopy.distance import distance
from geoparser import Geoparser, GeoNamesAPI, OverpassAPI

class CorpusEvaluator:

  def __init__(self, dist_limit):
    self.parser = Geoparser()
    self.dist_limit = dist_limit

  def start_corpus(self, corpus_name):
    now = datetime.datetime.now()
    out_path = f'eval-{corpus_name}-{now}.txt'
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
          geoname_id = toponym.selected.geoname.id
          if position in self.gn_anns:
            self.gn_anns[position].append(geoname_id)
          else:
            self.gn_anns[position] = [geoname_id]
      for match in cluster.local_matches:
        for position in match.positions:
          self.osm_anns[position] = match.elements

  def test_gold_geoname(self, position, name, geoname_id):
    self.doc_total_tests += 1

    if position in self.gn_anns and geoname_id in self.gn_anns[position]:
      self.doc_tests_passed += 1
    else:
      self.log_line(f'Missing geoname {name} ({geoname_id}) at {position}')

  def test_gold_coordinate(self, position, name, lat, lng):
    self.doc_total_tests += 1

    if position in self.osm_anns:
      osm_elements = self.osm_anns[position]
      csv_reader = OverpassAPI.load_all_coordinates(osm_elements)
      coords = map(lambda r: (float(r[0]), float(r[1])), csv_reader)
      if len(coords) == 0:
        self.log_line(f'No coordinates from OSM elements for {name}: {osm_elements}')
        return

    elif position in self.gn_anns:
      geoname_ids = self.gn_anns[position]
      coords = []
      for geoname_id in geoname_ids:
        geoname = GeoNamesAPI.get_geoname(geoname_id)
        coords.append((geoname.lat, geoname.lng))

    else:
      self.log_line(f'Missing annotation for {name} at {position}')
      return

    if self.coords_in_range(coords, lat, lng):
      self.doc_tests_passed += 1
    else:
      self.log_line(f'Wrong coordinate for {name} at {position}')

  def coords_in_range(self, coords, target_lat, target_lng):
    lat_sum = lng_sum = 0.0
    count = 0
    for lat, lng in coords:
      lat_sum += lat
      lng_sum += lng
      count += 1
    avg_lat = lat_sum / count
    avg_lng = lng_sum / count
    dist = distance((avg_lat, avg_lng), (target_lat, target_lng))
    return dist.km < self.dist_limit

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
