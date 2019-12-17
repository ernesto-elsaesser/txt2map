import os
import logging
import csv
from geoparser import Geoparser, GeoNamesCache, OverpassAPI, GeoUtil

class Match:

  def __init__(self, reference, distance, is_full):
    self.reference = reference
    self.distance = distance
    self.is_full = is_full

  def dist_str(self):
    return f'{self.distance:.2f}'


class Annotation:

  def __init__(self, position, phrase, lat, lon, geoname_id):
    self.position = position
    self.phrase = phrase
    self.lat = lat
    self.lon = lon
    self.geoname_id = geoname_id
    self.global_match = None
    self.local_match = None
    self.remark = ''

  def _matches(self):
    return filter(lambda m: m != None, [self.global_match, self.local_match])

  def rec_type(self):
    if self.global_match != None:
      if self.global_match.is_full: return 2
      if self.local_match == None: return 1
    if self.local_match != None:
      return 2 if self.local_match.is_full else 1
    return 0

  def res_type(self):
    if self.global_match != None:
      return 2
    elif self.local_match != None:
      return 1
    else:
      return 0

  def match_dists(self):
    md = glr = gld = lcr = lcd = ''
    if self.global_match != None:
      glr = self.global_match.reference
      gld = self.global_match.dist_str()
      md = gld
      dist = self.global_match.distance
    if self.local_match != None:
      glr = self.local_match.reference
      gld = self.local_match.dist_str()
      if md == '' or self.local_match.distance < dist:
        md = gld
    return (glr, gld, lcr, lcd, md)

  def recognized(self):
    return self.global_match != None or self.local_match != None

  def resolved_accurately(self, accuracy_km):
    if self.global_match != None:
      if self.global_match.distance < accuracy_km:
        return True
    if self.local_match != None:
      if self.local_match.distance < accuracy_km:
        return True
    return False


class Result:

  def __init__(self, doc, global_, local):
    self.doc = doc
    self.global_ = global_
    self.local = local
    self.annotations = []


class CorpusEvaluator:

  def __init__(self, geoparser):
    self.parser = geoparser
    self.results = {}

  def start_document(self, document, text):
    logging.info('--- %s ---', document)
    self.document = document
    global_ = {}
    local = {}

    doc = self.parser.parse(text)
    for toponym, positions in doc.positions.items():
      for position in positions:
        global_[position] = toponym

    for key, context in doc.local_contexts.items():
      for toponym, positions in context.positions.items():
        for position in positions:
          tupel = (key, toponym)
          if position in local:
            local[position].append(tupel)
          else:
            local[position] = [tupel]

    self.results[document] = Result(doc, global_, local)

  def verify_annotation(self, annotation):
    result = self.results[self.document]
    a = annotation

    if a.position in result.global_:
      toponym = result.global_[a.position]
      geoname = result.doc.geonames[toponym]
      if a.geoname_id == geoname.id:
        distance = 0.0
      else:
        distance = GeoUtil.distance(a.lat, a.lon, geoname.lat, geoname.lon)
      full_match = toponym == a.phrase
      a.global_match = Match(str(geoname.id), distance, full_match)
    
    if a.position in result.local:
      tupels = result.local[a.position]
      best_match = None
      best_full = None
      min_dist = float('inf')
      min_dist_full = float('inf')
      for key, toponym in tupels:
        full_match = toponym == a.phrase
        elements = result.doc.local_contexts[key].osm_elements[toponym]
        json_elements = self.parser.osm_loader.load_geometries(elements)
        for e in json_elements:
          reference = e['type'] + '/' + str(e['id'])
          distance = GeoUtil.osm_element_distance(a.lat, a.lon, e)
          if distance < min_dist:
            min_dist = distance
            best_match = Match(reference, distance, full_match)
          if full_match and distance < min_dist_full:
            min_dist_full = distance
            best_full = Match(reference, distance, full_match)
      a.local_match = best_full or best_match

    result.annotations.append(a)

  def document_summary(self, accuracy_km, document=None):
    d = document or self.document
    return self._summary(self.results[d].annotations, accuracy_km)

  def corpus_summary(self, accuracy_km):
    all_annotations = sum([r.annotations for r in self.results.values()], [])
    return self._summary(all_annotations, accuracy_km)

  def results_csv(self):
    lines = 'Document\tPos\tPhrase\tRec\tRes\tMin. Dist.\tGlobal\tGlobal Dist.\tLocal\tLocal Dist.\tRemark\n'
    for d in self.results:
      for a in self.results[d].annotations:
        p = a.position
        rec = a.rec_type()
        res = a.res_type()
        (glr, gld, lcr, lcd, md) = a.match_dists()
        rem = a.remark
        lines += f'{d}\t{p}\t{a.phrase}\t{rec}\t{res}\t{md}\t{glr}\t{gld}\t{lcr}\t{lcd}\t{rem}\n'
    return lines

  def _summary(self, annotations, accuracy_km):
    total = len(annotations)
    if total == 0:
      return 'no annotations'
    recognized = [a for a in annotations if a.recognized()]
    resolved = [a for a in annotations if a.resolved_accurately(accuracy_km)]
    p_recognized = int((len(recognized)/total) * 100)
    p_resolved = int((len(resolved)/total) * 100)
    return f'{total} annotations, {p_recognized}% recognized, {p_resolved}% resolved'
