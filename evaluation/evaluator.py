import os
import json
import urllib
from geoparser import GeoNamesCache, OSMLoader, GeoUtil, GeoNamesAPI

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
      pending += doc.get_all('ner', group)

    for g in gold_doc.get_all('gld'):
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
    pending = doc.get_all('rec')

    for g in gold_doc.get_all('gld'):
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

  def __init__(self, gold_group=None, tolerance_osm=0.2):
    self.gold_group = gold_group
    self.tol_osm = tolerance_osm
    self.gns_cache = GeoNamesCache()
    self.wiki_coords_cache = {}
    self.correct = 0
    self.incorrect = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    corrects = []
    incorrects = []
    missed = []
    pending = doc.get_all('res')

    for g in gold_doc.get_all('gld', self.gold_group):
      matches = [a for a in pending if self._matches(a, g)]
      pending = [a for a in pending if a not in matches]

      if len(matches) == 0:
        missed.append(g)
        continue

      wiki_urls = [a.data for a in matches if a.group == 'wik']
      geo_ids = [a.data for a in matches if a.group == 'glo']
      osm_refs = [a.data for a in matches if a.group.startswith('clu-')]
      resolved = False
      if g.group == 'gns':
        resolved = self._global_hit(g.data, geo_ids)
        if not resolved and len(osm_refs) > 0:
          gold_geo = self.gns_cache.get(g.data)
          resolved = self._local_hit(gold_geo.lat, gold_geo.lon, osm_refs)
        if not resolved and len(wiki_urls) > 0:
          resolved = self._wiki_gns_hit(g.data, wiki_urls)
      else:
        resolved = self._local_hit(g.data[0], g.data[1], osm_refs)
        if not resolved and len(wiki_urls) > 0:
          resolved = self._wiki_coord_hit(g.data[0], g.data[1], wiki_urls)

      if resolved:
        corrects.append(g)
      else:
        incorrects.append(g)

    self.correct += len(corrects)
    self.incorrect += len(incorrects)
    self._print_if_not_empty(incorrects, 'RES INCORRECT')
    self.false_pos += len(pending)
    self._print_if_not_empty(pending, 'RES FALSE POS')
    self.false_neg += len(missed)
    self._print_if_not_empty(missed, 'RES FALSE NEG')


  def _global_hit(self, gold_id, geoname_ids):
    gold_ids = self._related_ids(gold_id)
    for gid in geoname_ids:
      if gid in gold_ids:
        return True
      ids = self._related_ids(gid)
      if gold_id in ids:
        return True
    return False

  def _related_ids(self, geoname_id):
    hierarchy = self.gns_cache.get_hierarchy(geoname_id)
    name = hierarchy[-1].name
    related = [g for g in hierarchy][-3:]  # accept up to two levels above
    return [g.id for g in related if name in g.name or g.name in name]

  def _local_hit(self, gold_lat, gold_lon, osm_refs):
    for refs in osm_refs:
      elements = OSMLoader.load_geometries(refs)
      dist = GeoUtil.osm_element_distance(gold_lat, gold_lon, elements[0])
      if dist < self.tol_osm:
        return True
      elif dist < self.tol_osm + 30.0:  # max dist between two elements
        for e in elements[1:]:
          d = GeoUtil.osm_element_distance(gold_lat, gold_lon, e)
          if d < self.tol_osm:
            return True
      return False

  def _wiki_gns_hit(self, gold_id, wiki_urls):
    geoname_ids = []
    for url in wiki_urls:
      geoname_id = self._geoname_for_wiki_url(url)
      if geoname_id != None:
        geoname_ids.append(geoname_id)
    return self._global_hit(gold_id, geoname_ids)

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
      results = self.gns_cache.search(title)[:25]
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

  def _wiki_coord_hit(self, gold_lat, gold_lon, urls):
    for url in urls:
      if url in self.wiki_coords_cache:
        coords = self.wiki_coords_cache[url]
      else:
        coords = GeoUtil.coordinates_for_wiki_url(url)
        self.wiki_coords_cache[url] = coords
      for lat, lon in coords:
        dist = GeoUtil.distance(lat, lon, gold_lat, gold_lon)
        if dist < self.tolerance:
          print('COORD HIT: ' + url)
          return True
      return False

  def _metrics(self):
    metrics = {'TolOSM': self.tol_osm}
    total = self.correct + self.incorrect + self.false_neg
    if total > 0:
      metrics['Acc'] = self.correct / total
      resolved = self.correct + self.incorrect
      if resolved > 0:
        metrics['AccResol'] = self.correct / resolved
        metrics['Resol%'] = resolved / total
    return metrics
