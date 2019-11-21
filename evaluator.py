import os
import datetime
from geopy.distance import distance
import parser
import geonames
import osm

class CorpusEvaluator:

  def __init__(self, dist_limit):
    self.parser = parser.Geoparser()
    self.dist_limit = dist_limit

  def start_corpus(self, corpus_name):
    output_dir = f'eval/{corpus_name}'
    if not os.path.exists(output_dir):
      os.mkdir(output_dir)
    now = datetime.datetime.now()
    out_path = f'{output_dir}/results-{now.date()}.txt'
    self.out = open(out_path, mode='w', encoding='utf-8')
    header = f'Evaluation with the {corpus_name} corpus at {now.time()}:'
    self.out.write(header + '\n')
    self.doc_count = 0
    self.total_tests = 0
    self.tests_passed = 0

  def start_document(self, document_id, text):
    self.doc_id = document_id
    self.doc_total_tests = 0
    self.doc_tests_passed = 0
    self.errors = []
    self.gn_anns = {}
    self.osm_anns = {}

    clusters = self.parser.parse(text)
    for cluster in clusters:
      for match in cluster.matches:
        for position in match.positions:
          self.gn_anns[position] = match.geoname.id
      for match in cluster.local_matches:
        for position in match.positions:
          self.osm_anns[position] = match.elements

  def test_gold_geoname(self, position, geoname_id):
    if position in self.gn_anns and self.gn_anns[position] == geoname_id:
      self.doc_total_tests += 1
      self.doc_tests_passed += 1
      return

    geoname = geonames.GeoNamesAPI.get_geoname(geoname_id)
    self.test_gold_coordinate(position, geoname.lat, geoname.lng)

  def test_gold_coordinate(self, position, lat, lng):
    self.doc_total_tests += 1

    if position not in self.osm_anns:
      return

    osm_elements = self.osm_anns[position]
    found_coord = self.get_avg_coord(osm_elements)
    target_coord = (lat, lng)
    dist = distance(target_coord, found_coord)
    if dist.km < self.dist_limit:
      self.doc_tests_passed += 1

  def get_avg_coord(self, osm_elements):
    csv_reader = osm.OverpassAPI.load_all_coordinates(osm_elements)
    lat_sum = lng_sum = 0.0
    count = 0
    for row in csv_reader:
      lat_sum += float(row[0])
      lng_sum += float(row[1])
      count += 1
    avg_lat = lat_sum / count
    avg_lng = lng_sum / count
    return (avg_lat, avg_lng)

  def finish_document(self):
    total = self.doc_total_tests
    passed = self.doc_tests_passed
    percentage = 100.0 if total == 0 else passed/total
    self.total_tests += total
    self.tests_passed += passed
    self.doc_count += 1
    summary = f'Document {self.doc_id}: {passed}/{total} ({percentage:.1f}%)'
    self.out.write(summary + '\n')

  def finish_corpus(self):
    total = self.total_tests
    passed = self.tests_passed
    percentage = 100.0 if total == 0 else passed/total
    footer = f'Overall ({self.doc_count} documents): {passed}/{total} ({percentage:.1f}%)'
    self.out.write(footer)
    self.out.close()
