import os
import datetime
import logging
from geopy.distance import distance
import parser
import geonames
import osm

class CorpusEvaluator:

  def __init__(self, dist_limit):
    self.parser = parser.Geoparser()
    self.dist_limit = dist_limit
    self.base_dir = 'eval'
    if not os.path.exists(self.base_dir):
      os.mkdir(self.base_dir)

  def start_corpus(self, corpus_name):
    output_dir = f'{self.base_dir}/{corpus_name}'
    if not os.path.exists(output_dir):
      os.mkdir(output_dir)
    now = datetime.datetime.now()
    out_path = f'{output_dir}/results-{now.date()}.txt'
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
      for match in cluster.all_matches:
        for position in match.positions:
          if position in self.gn_anns:
            self.gn_anns[position].append(match.geoname.id)
          else:
            self.gn_anns[position] = [match.geoname.id]
      for match in cluster.local_matches:
        for position in match.positions:
          self.osm_anns[position] = match.elements

  def test_gold_geoname(self, position, geoname_id):
    self.doc_total_tests += 1

    if position in self.gn_anns and geoname_id in self.gn_anns[position]:
      self.doc_tests_passed += 1
    else:
      self.log_line(f'Missing geoname {geoname_id} at {position}')

  def test_gold_coordinate(self, position, lat, lng):
    self.doc_total_tests += 1

    if position in self.osm_anns:
      osm_elements = self.osm_anns[position]
      csv_reader = osm.OverpassAPI.load_all_coordinates(osm_elements)
      coords = map(lambda r: (float(r[0]), float(r[1])), csv_reader)
      if len(coords) == 0:
        urls = ' , '.join(e.url() for e in osm_elements)
        self.log_line(f'No coordinates for OSM elements {urls}')
        return

    elif position in self.gn_anns:
      geoname_ids = self.gn_anns[position]
      coords = []
      for geoname_id in geoname_ids:
        geoname = geonames.GeoNamesAPI.get_geoname(geoname_id)
        coords.append((geoname.lat, geoname.lng))

    else:
      self.log_line(f'Missing annotation at {position}')
      return

    if self.coords_in_range(coords, lat, lng):
      self.doc_tests_passed += 1
    else:
      self.log_line(f'Wrong coordinate at {position}')

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
