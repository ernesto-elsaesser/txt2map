from geoparser import GeoNamesCache, OSMLoader, GeoUtil, GeoNamesAPI

class Evaluator:

  def print_metrics(self):
    metrics = self._metrics()
    values = [f'{k}: {v:.3f}' for k, v in metrics.items()]
    print(', '.join(values))

  def _matches(self, a, gold):
    return a.pos == gold.pos #and len(a.phrase) >= len(gold.phrase) - 1

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


class RecogEvaluator(Evaluator):

  def __init__(self, layer='rec', gold_layer='rec', include_osm=True):
    self.layer = layer
    self.gold_layer = gold_layer
    self.include_osm = include_osm
    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    correct = []
    missed = []
    pending = doc.get_all(self.layer)
    if self.include_osm:
      for l in doc.layers():
        if l.startswith('clu-'):
          pending += doc.get_all(l)

    for g in gold_doc.get_all(self.gold_layer):
      prev_len = len(pending)
      pending = [a for a in pending if not self._matches(a, g)]
      if len(pending) < prev_len:
        correct.append(g)
      else:
        missed.append(g)

    self.true_pos += len(correct)
    self.false_pos += len(pending)
    self.false_neg += len(missed)

    self._print_if_not_empty(pending, 'REC FALSE POS')
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

  # tolerance_osm=None to ignore OSM results
  def __init__(self, gold_group=None, tolerance_osm=1):
    self.gold_group = gold_group
    self.tol_osm = tolerance_osm
    self.gns_cache = GeoNamesCache()
    self.correct = 0
    self.incorrect = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    corrects = []
    incorrects = []
    missed = []
    pending = doc.get_all('res')
    pending_clust = []
    if self.tol_osm != None:
      for l in doc.layers():
        if l.startswith('clu-'):
          pending_clust += doc.get_all(l)

    for g in gold_doc.get_all('res', self.gold_group):
      matches = [a for a in pending if self._matches(a, g)]
      pending = [a for a in pending if a not in matches]

      matches_clust = [a for a in pending_clust if self._matches(a, g)]
      pending_clust = [a for a in pending_clust if a not in matches_clust]

      if len(matches + matches_clust) == 0:
        missed.append(g)
        continue

      geo_ids = [a.data for a in matches]
      osm_refs = [a.data for a in matches_clust]
      resolved = False
      if g.group == 'gns':
        resolved = self._global_hit(g.data, geo_ids)
        if not resolved:
          gold_geo = self.gns_cache.get(g.data)
          resolved = self._local_hit(gold_geo.lat, gold_geo.lon, osm_refs)
      else:
        resolved = self._local_hit(g.data[0], g.data[1], osm_refs)

      if resolved:
        corrects.append(g)
      else:
        incorrects.append(g)

    self.incorrect += len(incorrects)
    self.correct += len(corrects)
    self.false_pos += len(pending + pending_clust)
    self.false_neg += len(missed)

    self._print_if_not_empty(pending + pending_clust, 'RES FALSE POS')
    self._print_if_not_empty(missed, 'RES FALSE NEG')
    self._print_if_not_empty(incorrects, 'RES INCORRECT')

  def _global_hit(self, gold_id, geoname_ids):
    gold_hierarchy = self.gns_cache.get_hierarchy(gold_id)
    gold_ids = [g.id for g in gold_hierarchy][-3:] # accept up to two levels above
    for gid in geoname_ids:
      if gid in gold_ids:
        return True
      hierarchy = self.gns_cache.get_hierarchy(gid)
      ids = [g.id for g in hierarchy]
      if gold_id in ids:
        return True
    return False

  def _local_hit(self, gold_lat, gold_lon, osm_refs):
    for refs in osm_refs:
      elements = OSMLoader.load_geometries(refs)
      dist = GeoUtil.osm_element_distance(gold_lat, gold_lon, elements[0])
      if dist < self.tol_osm:
        return True
      elif dist < self.tol_local + 30.0:  # max dist between two elements
        for e in elements[1:]:
          d = GeoUtil.osm_element_distance(gold_lat, gold_lon, e)
          if d < self.tol_osm:
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


class WikiResolEvaluator(Evaluator):

  def __init__(self, gold_group=None, tolerance=1):
    self.gold_group = gold_group
    self.tolerance = tolerance
    self.gns_cache = {}
    self.coords_cache = {}
    self.correct = 0
    self.incorrect = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    corrects = []
    incorrects = []
    missed = []
    pending = doc.get_all('res')

    for g in gold_doc.get_all('res', self.gold_group):
      matches = [a for a in pending if self._matches(a, g)]
      pending = [a for a in pending if a not in matches]

      if len(matches) == 0:
        missed.append(g)
        continue

      urls = [a.data for a in matches]
      resolved = False
      if g.group == 'gns':
        resolved = self._url_hit(g.data, urls)
        if not resolved:
          gold_geo = self.gns_cache[g.data]
          resolved = self._coord_hit(gold_geo.lat, gold_geo.lon, urls)
      else:
        resolved = self._coord_hit(g.data[0], g.data[1], urls)

      if resolved:
        corrects.append(g)
      else:
        incorrects.append(g)

    self.correct += len(corrects)
    self.incorrect += len(incorrects)
    self.false_pos += len(pending)
    self.false_neg += len(missed)

    self._print_if_not_empty(pending, 'RES FALSE POS')
    self._print_if_not_empty(missed, 'RES FALSE NEG')
    self._print_if_not_empty(incorrects, 'RES INCORRECT')

  def _url_hit(self, gold_id, urls):
    if gold_id in self.gns_cache:
      gold_url = self.gns_cache[gold_id].wiki_url
    else:
      full_geo = GeoNamesAPI.get_geoname(gold_id)
      self.gns_cache[gold_id] = full_geo
      if full_geo.wiki_url == None:
        return False
      gold_url = 'https://' + full_geo.wiki_url
    return gold_url in urls

  def _coord_hit(self, gold_lat, gold_lon, urls):
    for url in urls:
      if url in self.coords_cache:
        coords = self.coords_cache[url]
      else:
        coords = GeoUtil.coordinates_for_wiki_url(url)
        self.coords_cache[url] = coords
      for lat, lon in coords:
        dist = GeoUtil.distance(lat, lon, gold_lat, gold_lon)
        if dist < self.tolerance:
          return True
      return False

  def _metrics(self):
    metrics = {'Tol': self.tolerance}
    total = self.correct + self.incorrect + self.false_neg
    if total > 0:
      metrics['Acc'] = self.correct / total
      resolved = self.correct + self.incorrect
      if resolved > 0:
        metrics['AccResol'] = self.correct / resolved
        metrics['Resol%'] = resolved / total
    return metrics
