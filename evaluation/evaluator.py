import os
import json
import logging
from geoparser import Geoparser, GeoNamesCache, OverpassAPI, GeoUtil, Document


class GoldAnnotation:

  def __init__(self, position, phrase, lat, lon, geoname_id):
    self.position = position
    self.phrase = phrase
    self.lat = lat
    self.lon = lon
    self.geoname_id = geoname_id

  def __repr__(self):
    return f'{self.phrase} @ {self.position} [{self.geoname_id}]'


class CorpusEvaluator:

  def __init__(self, count_inexact, tolerance_km):
    self.inexact = count_inexact
    self.tolerance = tolerance_km

    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0
    self.ann_count = 0
    self.accurate = 0

  def start_document(self, doc, parser):
    self.doc = doc
    self.parser = parser
    recognized = doc.annotated_positions('rec')
    self.false_pos += len(set(recognized))

  def evaluate(self, gold):
    self.ann_count += 1
    pos = gold.position

    recognized = False

    for a in self.doc.get('rec', pos=pos):
      if self.inexact or a.phrase == gold.phrase:
        self.false_pos -= 1
        self.true_pos += 1
        recognized = True
        break

    if not recognized:
      self.false_neg += 1
      print(f'NOT RECOGNIZED: {gold}')
      return

    resolved_within = False

    for a in self.doc.get('res', pos=pos):
      
      if a.group == 'sel':  # global
        if gold.geoname_id == a.data:
          resolved_within = True
          break
        else:
          geoname = self.parser.gns_cache.get(a.data)
          dist = GeoUtil.distance(gold.lat, gold.lon, geoname.lat, geoname.lon)
          if dist < self.tolerance:
            resolved_within = True
            break

      elif a.group.startswith('cl'): # local
        elements = self.parser.osm_loader.load_geometries(a.data)
        dist = GeoUtil.osm_element_distance(gold.lat, gold.lon, elements[0])
        if dist < self.tolerance:
          resolved_within = True
          break
        elif dist < self.tolerance + 30.0: # max dist between two elements
          for e in elements[1:]:
            d = GeoUtil.osm_element_distance(gold.lat, gold.lon, e)
            if d < dist:
              resolved_within = True
              break
          if resolved_within: break
        
    if resolved_within:
      self.accurate += 1
    else:
      print(f'NOT RESOLVED: {gold}')

  def metrics_str(self):
    if self.ann_count == 0:
      return (1.0, 1.0, 1.0, 1.0)

    p = self.true_pos / (self.true_pos + self.false_pos)
    r = self.true_pos / (self.true_pos + self.false_neg)
    f1 = (2 * p * r) / (p + r)
    acc = self.accurate / self.ann_count
    acc_r = self.accurate / self.true_pos

    am = f'Acc@{self.tolerance:.1f}km'
    return f'P: {p:.3f} R: {r:.3f} F1: {f1:.3f} {am}: {acc:.3f} ({acc_r:.3f} for resol only)'

