import os
import logging
import json
import sqlite3
from osm2geojson import json2geojson
from geoparser import Geoparser, GeoNamesCache, OverpassAPI, GeoUtil


class Annotation:

  def __init__(self, position, name):
    self.position = position
    self.name = name
    self.present = True
    self.correct = True
    self.distance = 0


class Result:

  def __init__(self, geonames, osm_elements):
    self.geonames = geonames
    self.osm_elements = osm_elements
    self.annotations = []


class CorpusEvaluator:

  def __init__(self, geoparser, accuracy_km):
    self.dist_limit = accuracy_km
    self.parser = geoparser
    self.gns_cache = geoparser.resolver.gns_cache
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
          geonames[position] = toponym.geoname
      for match in cluster.local_matches:
        for position in match.positions:
          if position in osm_elements:
            osm_elements[position] += match.elements
          else:
            osm_elements[position] = match.elements

    self.results[self.corpus][document] = Result(geonames, osm_elements)

  def geoname_to_coordinates(self, geoname_id):
    geoname = self.gns_cache.get(geoname_id)
    return (geoname.lat, geoname.lng)

  def verify_annotation(self, position, name, lat, lng):
    c, d = self.corpus, self.document
    result = self.results[c][d]
    ann = Annotation(position, name)

    if position in result.geonames:
      geoname = result.geonames[position]
      geometry = GeoUtil.make_point(geoname.lat, geoname.lng)
      ann.distance = GeoUtil.distance_beyond_tolerance(
          lat, lng, geometry, self.dist_limit)
    elif position in result.osm_elements:
      osm_elements = result.osm_elements[position]
      feature_collection = self._get_osm_element_geometries(osm_elements)
      ann.distance = GeoUtil.min_distance_beyond_tolerance(
          lat, lng, feature_collection, self.dist_limit)
    else:
      ann.present = False
      ann.correct = False

    if ann.distance > 0:
      ann.correct = False

    self.results[c][d].annotations.append(ann)

  def document_summary(self, corpus=None, document=None):
    c = corpus or self.corpus
    d = document or self.document
    result = self.results[c][d]
    return self._summary(result.annotations)

  def corpus_summary(self, corpus=None):
    c = corpus or self.corpus
    results = self.results[c]
    all_annotations = sum([r.annotations for r in results.values()], [])
    return self._summary(all_annotations)

  def document_report(self, corpus=None, document=None):
    c = corpus or self.corpus
    d = document or self.document
    result = self.results[c][d]
    summary = self.document_summary(corpus=c, document=d)
    report = f'{d}: {summary}\n'
    for a in result.annotations:
      if a.correct: continue
      if a.present:
        report += f'- Coordinate off by {a.distance:.1f} for {a.name} at {a.position}\n'
      else:
        report += f'- Missing annotation for {a.name} at {a.position}\n'
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

  def _get_osm_element_geometries(self, osm_elements):
    json_response = OverpassAPI.load_geometries(osm_elements)
    return json2geojson(json_response)

  def _summary(self, annotations):
    total = len(annotations)
    if total == 0:
      return 'no annotations'
    present = [a for a in annotations if a.present]
    correct = [a for a in annotations if a.correct]
    rel_present = int((len(present)/total) * 100)
    rel_correct = int((len(correct)/total) * 100)
    return f'{total} annotations, {rel_present}% recognized, {rel_correct}% resolved'
