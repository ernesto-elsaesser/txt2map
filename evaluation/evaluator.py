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
    self.remark = ''

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

  def start_document(self, document, text):
    logging.info('--- %s ---', document)
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

    self.results[document] = Result(geonames, osm_elements)

  def verify_annotation(self, annotation):
    result = self.results[self.document]
    a = annotation
    geoname_match = False

    if a.position in result.geonames:
      geoname = result.geonames[a.position]
      a.geoname = geoname
      a.distance = GeoUtil.distance(a.lat, a.lng, geoname.lat, geoname.lng)
      geoname_match = a.distance == 0
    
    if a.position in result.osm_elements and not geoname_match:
      elements = result.osm_elements[a.position]
      osm_json = OverpassAPI.load_geometries(elements)
      (dist, element) = GeoUtil.closest_osm_element(a.lat, a.lng, osm_json)
      if a.distance == None or a.distance > dist:
        a.osm_element = element
        a.distance = dist
        a.geoname = None

    result.annotations.append(a)

  def document_summary(self, accuracy_km, document=None):
    d = document or self.document
    return self._summary(self.results[d].annotations, accuracy_km)

  def corpus_summary(self, accuracy_km):
    all_annotations = sum([r.annotations for r in self.results.values()], [])
    return self._summary(all_annotations, accuracy_km)

  def results_csv(self):
    lines = 'Document\tPosition\tName\tRemark\tCoordinate\tSource\tID\tDistance\n'
    for d in self.results:
      for a in self.results[d].annotations:
        lines += f'{d}\t{a.position}\t{a.name}\t{a.remark}\t{a.lat},{a.lng}\t'
        if a.distance == None:
          lines += f'\t\t\n'
          continue
        if a.geoname != None:
          lines += f'GEO\t{a.geoname.id}\t{a.distance:.2f}\n'
        else:
          lines += f'OSM\t{a.osm_element}\t{a.distance:.2f}\n'
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
