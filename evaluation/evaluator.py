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

  def __init__(self, geoparser, count_inexact, measure_defaults, tolerance_km, save_dir):
    self.parser = geoparser
    self.inexact = count_inexact
    self.res_global_group = 'def' if measure_defaults else 'heur'
    self.tolerance = tolerance_km
    self.save_dir = save_dir

    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0
    self.ann_count = 0
    self.accurate = 0

  def start_document(self, document_id, text):
    
    if self.save_dir != None:
      file_path = f'{self.save_dir}/{document_id}.json'
      if os.path.exists(file_path):
        with open(file_path, 'r') as f:
          annotations = json.load(f)
        self.doc = Document(text, annotations)
      else:
        self.doc = self.parser.parse(text)
        with open(file_path, 'w') as f:
          json.dump(self.doc.annotations, f)
    else:
        self.doc = self.parser.parse(text)

    recognized = self.doc.annotated_positions('rec')
    self.false_pos += len(set(recognized))

  def evaluate(self, gold):
    self.ann_count += 1
    pos = gold.position

    recognized = False

    for phrase, _, _ in self.doc.iter_pos(pos, 'rec'):
      if self.inexact or phrase == gold.phrase:
        self.false_pos -= 1
        self.true_pos += 1
        recognized = True
        break

    if not recognized:
      self.false_neg += 1
      print(f'NOT RECOGNIZED: {gold}')
      return

    resolved_within = False

    for phrase, group, data in self.doc.iter_pos(pos, 'res'):
      
      if group == self.res_global_group:  # global
        if gold.geoname_id == data:
          resolved_within = True
          break
        else:
          geoname = self.parser.gns_cache.get(data)
          dist = GeoUtil.distance(gold.lat, gold.lon, geoname.lat, geoname.lon)
          if dist < self.tolerance:
            resolved_within = True
            break

      elif group.startswith('loc'): # local
        elements = self.parser.osm_loader.load_geometries(data)
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

