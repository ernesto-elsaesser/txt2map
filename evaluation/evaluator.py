import os
import json
import urllib
from geoparser import Datastore, Layer, GeoUtil, GeoNamesAPI

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

  def __init__(self, layer=Layer.lres, gold_group=None, measure_accuracy=True, tolerance_geonames=161, tolerance_raw=0.2, geonames_by_dist=False):
    self.layer = layer
    self.gold_group = gold_group
    self.skip_acc = not measure_accuracy
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

    res_indices = doc.annotations_by_index(Layer.gres)

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

      if self.skip_acc:
        corrects.append(g)
        continue

      resolved = False
      if g.group == 'geonames':
        if a.group == 'wiki':
          resolved = self._wiki_gns_hit(g.data, a.data)
        elif a.group == 'global':
          if self.gns_by_dist:
            gold_geo = Datastore.get_geoname(g.data)
            resolved = self._gns_coord_hit(gold_geo.lat, gold_geo.lon, a.data, self.tol_gns)
          else:
            resolved = self._gns_hit(g.data, a.data)
        elif a.group == 'local':
          gold_geo = Datastore.get_geoname(g.data)
          resolved = self._osm_hit(gold_geo.lat, gold_geo.lon, a.data, self.tol_gns)
      else:
        if a.group == 'wiki':
          resolved = self._wiki_coord_hit(g.data[0], g.data[1], a.data)
        elif a.group == 'global':
          resolved = self._gns_coord_hit(g.data[0], g.data[1], a.data, self.tol_raw)
          if not resolved:
            print('WRONG GEO MATCH!')
        elif a.group == 'local':
          resolved = self._osm_hit(g.data[0], g.data[1], a.data, self.tol_raw)

      if resolved:
        corrects.append(g)
      else:
        incorrects.append(g)

    self.correct += len(corrects)
    self.incorrect += len(incorrects)
    self._print_if_not_empty(incorrects, 'RES INCORRECT')
    self._print_if_not_empty(missed, 'RES MISSED')


  def _gns_hit(self, gold_id, geoname_id):
    gold_ids = self._related_ids(gold_id)
    if geoname_id in gold_ids:
      return True
    related_ids = self._related_ids(geoname_id)
    if gold_id in related_ids:
      return True
    return False

  def _related_ids(self, geoname_id):
    hierarchy = Datastore.get_hierarchy(geoname_id)
    name = hierarchy[-1].name
    related = [g for g in hierarchy][-3:]  # accept up to two levels above
    return [g.id for g in related if name in g.name or g.name in name]

  def _gns_coord_hit(self, gold_lat, gold_lon, geoname_id, tol):
    geo = Datastore.get_geoname(geoname_id)
    dist = GeoUtil.distance(geo.lat, geo.lon, gold_lat, gold_lon)
    return dist < tol

  def _osm_hit(self, gold_lat, gold_lon, osm_refs, tol):
    elements = Datastore.load_osm_geometries(osm_refs)
    dist = GeoUtil.osm_element_distance(gold_lat, gold_lon, elements[0])
    osm_diameter = Datastore.osm_search_dist * 2
    if dist < tol:
      return True
    elif dist < tol + osm_diameter: # correct local context, try other elements
      for e in elements[1:]:
        d = GeoUtil.osm_element_distance(gold_lat, gold_lon, e)
        if d < tol:
          return True
    return False

  def _wiki_gns_hit(self, gold_id, wiki_url):
    geoname_id = self._geoname_for_wiki_url(wiki_url)
    if geoname_id == None:
      return False
    return self._gns_hit(gold_id, geoname_id)

  def _geoname_for_wiki_url(self, url):
    title = url.replace('https://en.wikipedia.org/wiki/', '')
    title = title.replace('_', ' ')

    dirname = os.path.dirname(__file__)
    cache_path = f'{dirname}/data/wiki.json'
    if os.path.exists(cache_path):
      with open(cache_path, 'r') as f:
        cache = json.load(f)
    else:
      cache = {}

    if title in cache:
      geoname_id = cache[title]
    else:
      geoname_id = ''
      results = Datastore.search(title)[:25]
      for g in results:
        full_geo = GeoNamesAPI.get_geoname(g.id)
        if full_geo.wiki_url == None:
          continue
        wiki_url = full_geo.wiki_url
        if '%' in wiki_url:
          print(wiki_url)
        wiki_url = 'https://' + urllib.parse.unquote(wiki_url)
        if wiki_url == url:
          geoname_id = g.id
          break

      cache[title] = geoname_id
      with open(cache_path, 'w') as f:
        json.dump(cache, f)

    if geoname_id == '':
      return None
    else:
      return geoname_id

  def _wiki_coord_hit(self, gold_lat, gold_lon, url):
    if url in self.wiki_coords_cache:
      coords = self.wiki_coords_cache[url]
    else:
      coords = GeoUtil.coordinates_for_wiki_url(url)
      self.wiki_coords_cache[url] = coords
    for lat, lon in coords:
      dist = GeoUtil.distance(lat, lon, gold_lat, gold_lon)
      if dist < self.tol_raw:
        print('COORD HIT: ' + url)
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
