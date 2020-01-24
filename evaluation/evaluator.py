import os
import json
import urllib
from geoparser import Datastore, Layer, GeoUtil, GeoNamesAPI, OverpassAPI

class Evaluator:

  def print_metrics(self):
    metrics = self._metrics()
    values = [f'{k}: {v:.3f}' for k, v in metrics.items()]
    print(', '.join(values))

  def _matches(self, a, gold):
    if a.pos != gold.pos:
      return False
    if a.phrase == gold.phrase:
      return True
    if a.phrase == gold.phrase + '.':
      return True
    if a.phrase + '.' == gold.phrase:
      return True
    return False

  def _print_if_not_empty(self, anns, msg):
    if len(anns) > 0:
      names = [a.phrase for a in anns]
      print(f'{msg}: {names}')


class Counter(Evaluator):

  def __init__(self, layer, group=None, count_gold=False):
    self.layer = layer
    self.group = group
    self.count_gold = count_gold
    self.layer_count = 0
    self.group_count = 0

  def evaluate(self, doc, gold_doc):
    d = gold_doc if self.count_gold else doc
    anns = d.get_all(self.layer)
    self.layer_count += len(anns)
    if self.group != None:
      group_anns = [a for a in anns if a.group == self.group]
      if len(group_anns) > 0:
        self.group_count += len(group_anns)
        print([a.phrase for a in group_anns])

  def _metrics(self):
    metrics = {self.layer: self.layer_count}
    if self.group != None:
      metrics[self.group] = self.group_count
    return metrics


class NEREvaluator(Evaluator):

  def __init__(self, groups=['loc']):
    self.groups = groups
    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    correct = []
    missed = []
    pending = []
    for group in self.groups:
      pending += doc.get_all(Layer.ner, group)

    for g in gold_doc.get_all(Layer.gold):
      matches = [a for a in pending if self._matches(a, g)]
      pending = [a for a in pending if a not in matches]

      if len(matches) > 0:
        correct.append(g)
      else:
        missed.append(g)

    self.true_pos += len(correct)
    self.false_neg += len(missed)
    self._print_if_not_empty(missed, 'REC FALSE NEG')
    self.false_pos += len(pending)
    self._print_if_not_empty(pending, 'REC FALSE POS')

  def _metrics(self):
    metrics = {}
    recognized = self.true_pos + self.false_pos
    if recognized > 0:
      p = self.true_pos / recognized
      metrics['P'] = p
    wookie = self.true_pos + self.false_neg
    if wookie > 0:
      r = self.true_pos / wookie
      metrics['R'] = r
    if self.true_pos > 0:
      metrics['F1'] = (2 * p * r) / (p + r)
    return metrics



class RecogEvaluator(Evaluator):

  def __init__(self):
    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    correct = []
    missed = []
    pending = doc.get_all(Layer.topo)

    for g in gold_doc.get_all(Layer.gold):
      matches = [a for a in pending if self._matches(a, g)]
      pending = [a for a in pending if a not in matches]

      if len(matches) > 0:
        correct.append(g)
      else:
        missed.append(g)

    self.true_pos += len(correct)
    self.false_pos += len(pending)
    self._print_if_not_empty(pending, 'REC FALSE POS')
    self.false_neg += len(missed)
    self._print_if_not_empty(missed, 'REC FALSE NEG')

  def _metrics(self):
    metrics = {}
    recognized = self.true_pos + self.false_pos
    if recognized > 0:
      p = self.true_pos / recognized
      metrics['P'] = p
    wookie = self.true_pos + self.false_neg
    if wookie > 0:
      r = self.true_pos / wookie
      metrics['R'] = r
    if self.true_pos > 0:
      metrics['F1'] = (2 * p * r) / (p + r)
    return metrics


class ResolEvaluator(Evaluator):

  def __init__(self, layer=Layer.lres, gold_group=None, tolerance_geonames=161, tolerance_raw=2, geonames_by_dist=True):
    self.layer = layer
    self.gold_group = gold_group
    self.tol_gns = tolerance_geonames
    self.tol_raw = tolerance_raw
    self.gns_by_dist = geonames_by_dist
    self.wiki_coords_cache = {}
    self.correct = 0
    self.incorrect = 0
    self.false_neg = 0
    self.total = 0

  def evaluate(self, doc, gold_doc):
    corrects = []
    incorrects = []
    missed = []

    res_indices = doc.annotations_by_index(self.layer)

    for g in gold_doc.get_all(Layer.gold, self.gold_group):
      self.total += 1
      
      a = None
      for i in range(g.pos, g.end_pos()):
        if i in res_indices:
          a = res_indices[i]
          break

      if a == None:
        missed.append(g)
        continue

      if g.group == 'geonames':
        gold_geo = Datastore.get_geoname(g.data)
        gold_lat = gold_geo.lat
        gold_lon = gold_geo.lon
        tolerance = self.tol_gns
      elif g.group == 'raw':
        gold_lat = g.data[0]
        gold_lon = g.data[1]
        tolerance = self.tol_raw
      else:
        corrects.append(g)
        continue
      
      dist = GeoUtil.distance(a.data[0], a.data[1], gold_lat, gold_lon)
      if dist < tolerance:
        corrects.append(g)
      else:
        incorrects.append(g)

    self.correct += len(corrects)
    self.incorrect += len(incorrects)
    self._print_if_not_empty(incorrects, 'RES INCORRECT')
    self._print_if_not_empty(missed, 'RES MISSED')

  def _gns_hit(self, gold_lat, gold_lon, geoname_id, tol):
    geo = Datastore.get_geoname(geoname_id)
    dist = GeoUtil.distance(geo.lat, geo.lon, gold_lat, gold_lon)
    return dist < tol

  def _osm_hit(self, gold_lat, gold_lon, osm_refs, tol):
    bb_data = OverpassAPI.load_bounding_boxes(osm_refs)
    dist = GeoUtil.osm_minimum_distance(gold_lat, gold_lon, bb_data)
    return dist < tol

  def _wiki_hit(self, gold_lat, gold_lon, wiki_url, tol):
    # geoname_id = Datastore.geoname_for_wiki_url(wiki_url)
    # if geoname_id != None:
    #   if self._gns_hit(gold_lat, gold_lon, geoname_id, tol):
    #     return True
    coords = GeoUtil.coordinates_for_wiki_url(wiki_url)
    for lat, lon in coords:
      dist = GeoUtil.distance(lat, lon, gold_lat, gold_lon)
      if dist < tol:
        return True
    return False

  def _metrics(self):
    metrics = {'Total': self.total}
    if self.total > 0:
      metrics['Acc'] = self.correct / self.total
      resolved = self.correct + self.incorrect
      if resolved > 0:
        metrics['AccResol'] = self.correct / resolved
        metrics['Resol%'] = resolved / self.total
    metrics['TolGNS'] = self.tol_gns
    metrics['TolRaw'] = self.tol_raw
    return metrics
