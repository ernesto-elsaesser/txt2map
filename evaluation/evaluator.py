import os
import logging
import csv
from geoparser import Geoparser, GeoNamesCache, OverpassAPI, GeoUtil, OSMElement


class Annotation:

  def __init__(self, position, phrase, lat, lon, geoname_id):
    self.position = position
    self.phrase = phrase
    self.lat = lat
    self.lon = lon
    self.geoname_id = geoname_id
    self.recognized = False
    self.resolved = False
    self.resolved_local = False
    self.geoname = None
    self.geoname_dist = None
    self.osm_element = None
    self.osm_element_dist = None
    self.comment = ''

  def min_dist(self):
    min_dist = None
    if self.geoname_dist != None:
      min_dist = self.geoname_dist
    if self.osm_element_dist != None:
      if min_dist == None or min_dist > self.osm_element_dist:
        min_dist = self.osm_element_dist
    return min_dist

  def within(self, accuracy_km):
    dist = self.min_dist()
    if dist == None:
      return False
    return dist < accuracy_km


class Result:

  def __init__(self, doc, matches):
    self.doc = doc
    self.matches = matches
    self.annotations = []


class CorpusEvaluator:

  def __init__(self, geoparser):
    self.parser = geoparser
    self.results = {}

  def start_document(self, document, text):
    logging.info('--- %s ---', document)
    self.document = document
    matches = {}

    doc = self.parser.parse(text)
    for toponym, positions in doc.positions.items():
      for position in positions:
        matches[position] = [(False, toponym)]

    for context in doc.local_contexts.values():
      for toponym, positions in context.positions.items():
        for position in positions:
          if position in matches:
            matches[position].append((True, toponym))
          else:
            matches[position] = [(True, toponym)]

    self.results[document] = Result(doc, matches)

  def verify_annotation(self, annotation):
    result = self.results[self.document]
    a = annotation

    if a.position in result.matches:
      for is_local, toponym in result.matches[a.position]:
        if toponym != a.phrase:
          continue
        a.recognized = True

        if not is_local and toponym in result.doc.geonames:
          a.resolved = True
          g = result.doc.geonames[toponym]
          a.geoname = g
          if a.geoname_id == g.id:
            a.geoname_dist = 0.0
          else:
            a.geoname_dist = GeoUtil.distance(a.lat, a.lon, g.lat, g.lon)

        if is_local:
          for c in result.doc.local_contexts.values():
            if toponym not in c.osm_elements:
              continue

            a.resolved = True
            a.resolved_local = True

            elements = c.osm_elements[toponym]
            json_elements = self.parser.osm_loader.load_geometries(elements)

            a.osm_element_dist = float('inf')
            for e in json_elements:
              distance = GeoUtil.osm_element_distance(a.lat, a.lon, e)
              if distance < a.osm_element_dist:
                a.osm_element = OSMElement(e['id'], e['type'])
                a.osm_element_dist = distance

    result.annotations.append(a)

  def document_summary(self, accuracy_km, document=None):
    d = document or self.document
    return self._summary(self.results[d].annotations, accuracy_km)

  def corpus_summary(self, accuracy_km):
    all_annotations = sum([r.annotations for r in self.results.values()], [])
    return self._summary(all_annotations, accuracy_km)

  def results_csv(self):
    lines = 'document\tpos\tphrase\trec\tres\tres_loc\tmin_dist\tgeoname\tgn_dist\tosm\tosm_dist\tcomment\n'
    for d in self.results:
      for a in self.results[d].annotations:
        rec = 1 if a.recognized else 0
        res = 1 if a.resolved else 0
        resloc = 1 if a.resolved_local else 0
        lines += f'{d}\t{a.position}\t{a.phrase}\t{rec}\t{res}\t{resloc}\t'
        md = self._format_dist(a.min_dist())
        g = '' if a.geoname == None else str(a.geoname.id)
        gd = self._format_dist(a.geoname_dist)
        o = '' if a.osm_element == None else str(a.osm_element.reference())
        od = self._format_dist(a.osm_element_dist)
        lines += f'{md}\t{g}\t{gd}\t{o}\t{od}\t{a.comment}\n'
    return lines

  def _format_dist(self, dist):
    if dist == None:
      return ''
    return f'{dist:.2f}'

  def _summary(self, annotations, accuracy_km):
    total = len(annotations)
    if total == 0:
      return 'no annotations'
    recognized = [a for a in annotations if a.recognized]
    resolved = [a for a in annotations if a.within(accuracy_km)]
    p_recognized = int((len(recognized)/total) * 100)
    p_resolved = int((len(resolved)/total) * 100)
    return f'{total} annotations, {p_recognized}% recognized, {p_resolved}% resolved'
