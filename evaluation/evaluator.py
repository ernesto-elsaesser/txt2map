import os
import logging
import csv
from geoparser import Geoparser, GeoNamesCache, OverpassAPI, GeoUtil


class Annotation:

  def __init__(self, position, name, lat, lng):
    self.position = position
    self.name = name
    self.lat = lat
    self.lng = lng
    self.distance = None
    self.geoname = None
    self.osm_element = None
    self.remark = None

  def recognized(self):
    return self.geoname != None or self.osm_element != None

  def resolved(self, accuracy_km):
    return self.distance != None and self.distance < accuracy_km


class Result:

  def __init__(self, geonames, osm_elements):
    self.geonames = geonames
    self.osm_elements = osm_elements
    self.annotations = []


class CorpusEvaluator:

  def __init__(self, geoparser):
    self.parser = geoparser
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

  def verify_annotation(self, annotation):
    c, d, a = self.corpus, self.document, annotation
    result = self.results[c][d]
    geoname_match = False

    if a.position in result.geonames:
      geoname = result.geonames[a.position]
      geometry = GeoUtil.make_point(geoname.lat, geoname.lng)
      a.geoname = geoname
      a.distance = GeoUtil.distance_to_geometry(a.lat, a.lng, geometry)
      geoname_match = a.distance == 0
    
    if a.position in result.osm_elements and not geoname_match:
      elements = result.osm_elements[a.position]
      json_geometries = OverpassAPI.load_geometries(elements)
      (dist, element) = GeoUtil.min_distance_osm_element(a.lat, a.lng, json_geometries)
      a.osm_element = element
      a.distance = dist

    self.results[c][d].annotations.append(a)

  def document_summary(self, accuracy_km, corpus=None, document=None):
    c = corpus or self.corpus
    d = document or self.document
    result = self.results[c][d]
    return self._summary(result.annotations, accuracy_km)

  def corpus_summary(self, accuracy_km, corpus=None):
    c = corpus or self.corpus
    results = self.results[c]
    all_annotations = sum([r.annotations for r in results.values()], [])
    return self._summary(all_annotations, accuracy_km)

  def report_csv(self):
    lines = ''
    for c in self.results:
      for d in self.results[c]:
        for a in self.results[c][d].annotations:
          p = a.position
          n = a.name
          r = a.remark or ''
          dist = gid = osmref =''
          if a.distance != None:
            dist = f'{a.distance:.2f}'
          if a.geoname != None:
            gid = str(a.geoname.id)
          if a.osm_element != None:
            osmref = str(a.osm_element)
          lines += f'{c}\t{d}\t{p}\t{n}\t{r}\t{dist}\t{gid}\t{osmref}\n'
    return lines

  def _summary(self, annotations, accuracy_km):
    total = len(annotations)
    if total == 0:
      return 'no annotations'
    recognized = [a for a in annotations if a.recognized()]
    resolved = [a for a in annotations if a.resolved(accuracy_km)]
    p_recognized = int((len(recognized)/total) * 100)
    p_resolved = int((len(resolved)/total) * 100)
    return f'{total} annotations, {p_recognized}% recognized, {p_resolved}% resolved'
