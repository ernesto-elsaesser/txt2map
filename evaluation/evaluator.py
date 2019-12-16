import os
import logging
import csv
from geoparser import Geoparser, GeoNamesCache, OverpassAPI, GeoUtil

class Match:

  def __init__(self, reference, distance, is_global):
    self.reference = reference
    self.distance = distance
    self.is_global = is_global

  def __repr__(self):
    return f'{self.reference}:{self.distance:.2f}'


class Annotation:

  def __init__(self, position, name, lat, lon, geoname_id):
    self.position = position
    self.name = name
    self.lat = lat
    self.lon = lon
    self.geoname_id = geoname_id
    self.matches = []
    self.remark = ''

  def min_distance(self):
    if len(self.matches) == 0:
      return None
    return min(m.distance for m in self.matches)

  def has_global_match(self):
    global_matches = [m for m in self.matches if m.is_global]
    return len(global_matches) > 0

  def recognized(self):
    return len(self.matches) > 0

  def resolved(self, accuracy_km):
    min_dist = self.min_distance()
    if min_dist == None:
      return False
    return min_dist < accuracy_km


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
      for res_set in cluster.sets:
        for position in res_set.positions:
          geonames[position] = res_set.geoname()
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

    if a.position in result.geonames:
      geoname = result.geonames[a.position]
      reference = 'g' + str(geoname.id)
      if a.geoname_id == geoname.id:
        distance = 0.0
      else:
        distance = GeoUtil.distance(a.lat, a.lon, geoname.lat, geoname.lon)
      match = Match(reference, distance, True)
      a.matches.append(match)
    
    if a.position in result.osm_elements:
      elements = result.osm_elements[a.position]
      json_elements = self.parser.osm_loader.load_geometries(elements)
      for e in json_elements:
        distance = GeoUtil.osm_element_distance(a.lat, a.lon, e)
        reference = e['type'][0] + str(e['id'])
        match = Match(reference, distance, False)
        a.matches.append(match)

    result.annotations.append(a)

  def document_summary(self, accuracy_km, document=None):
    d = document or self.document
    return self._summary(self.results[d].annotations, accuracy_km)

  def corpus_summary(self, accuracy_km):
    all_annotations = sum([r.annotations for r in self.results.values()], [])
    return self._summary(all_annotations, accuracy_km)

  def results_csv(self):
    lines = 'Document\tPosition\tName\tResolved\tMin. Distance\tEntities\tRemark\n'
    for d in self.results:
      for a in self.results[d].annotations:
        p = a.position
        res = 0
        md = ''
        matches = ''
        rem = a.remark

        min_dist = a.min_distance()
        if min_dist != None:
          res = 1 if a.has_global_match() else 2
          md = f'{min_dist:.2f}'
          matches = ','.join(str(m) for m in a.matches)

        lines += f'{d}\t{p}\t{a.name}\t{res}\t{md}\t{matches}\t{rem}\n'
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
