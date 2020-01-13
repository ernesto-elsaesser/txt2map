from geoparser import GeoNamesCache, OSMLoader, GeoUtil

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

  def __init__(self, layer='rec', gold_layer='rec', include_clusters=True):
    self.layer = layer
    self.gold_layer = gold_layer
    self.incl_clusters = include_clusters
    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    correct = []
    missed = []
    pending = doc.get_all(self.layer)
    if self.incl_clusters:
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

  def __init__(self, layer='res', gold_layer='res', gold_group=None, tolerance_global=161, tolerance_local=1, include_clusters=True):
    self.layer = layer
    self.gold_layer = gold_layer
    self.gold_group = gold_group
    self.tol_global = tolerance_global
    self.incl_clusters = include_clusters
    self.tol_local = tolerance_local
    self.gns_cache = GeoNamesCache()
    self.accurate = 0
    self.inaccurate = 0
    self.false_neg = 0
    self.false_pos = 0

  def evaluate(self, doc, gold_doc):
    accurates = []
    inaccurates = []
    missed = []
    pending = doc.get_all(self.layer)
    if self.incl_clusters:
      for l in doc.layers():
        if l.startswith('clu-'):
          pending += doc.get_all(l)

    for g in gold_doc.get_all(self.gold_layer, self.gold_group):
      resolved = [a for a in pending if self._matches(a, g)]
      pending = [a for a in pending if not self._matches(a, g)]

      if len(resolved) == 0:
        missed.append(g)
        continue

      in_tolerance = False
      for a in resolved:
        if a.layer.startswith('clu-'):
          in_tolerance = self._local_res_in_tolerance(a, g)
        elif a.group == 'wik':
          in_tolerance = self._wiki_res_in_tolerance(a, g)
        else:
          in_tolerance = self._global_res_in_tolerance(a, g)
        if in_tolerance:
          break

      if in_tolerance:
        accurates.append(g)
      else:
        inaccurates.append(g)

    self.inaccurate += len(inaccurates)
    self.accurate += len(accurates)
    self.false_pos += len(pending)
    self.false_neg += len(missed)

    self._print_if_not_empty(pending, 'RES FALSE POS')
    self._print_if_not_empty(missed, 'RES FALSE NEG')
    self._print_if_not_empty(inaccurates, 'RES INACC')

  def _metrics(self):
    ts = f'<{self.tol_global}/{self.tol_local}>'
    metrics = {}
    total = self.accurate + self.inaccurate + self.false_neg
    if total > 0:
      metrics['Acc'+ts] = self.accurate / total
      resolved = self.accurate + self.inaccurate
      if resolved > 0:
        metrics['AccResol'+ts] = self.accurate / resolved
        metrics['Resol%'] = resolved / total
    return metrics

  def _wiki_res_in_tolerance(self, a, gold):
    (gold_lat, gold_lon) = self._gold_coords(gold)
    for arr in a.data:
      dist = GeoUtil.distance(arr[0], arr[1], gold_lat, gold_lon)
      if dist < self.tol_global:
        return True
    return False

  def _global_res_in_tolerance(self, a, gold):
    if gold.data == a.data:
      return True
    g = self.gns_cache.get(a.data)
    (gold_lat, gold_lon) = self._gold_coords(gold)
    dist = GeoUtil.distance(g.lat, g.lon, gold_lat, gold_lon)
    return dist < self.tol_global

  def _local_res_in_tolerance(self, a, gold):
    elements = OSMLoader.load_geometries(a.data)
    (gold_lat, gold_lon) = self._gold_coords(gold)
    dist = GeoUtil.osm_element_distance(gold_lat, gold_lon, elements[0])
    if dist < self.tol_local:
      return True
    elif dist < self.tol_local + 30.0:  # max dist between two elements
      for e in elements[1:]:
        d = GeoUtil.osm_element_distance(gold_lat, gold_lon, e)
        if d < self.tol_local:
          return True
    return False

  def _gold_coords(self, gold):
    if gold.group == 'gns':
      g = self.gns_cache.get(gold.data)
      return (g.lat, g.lon)
    else:
      return (gold.data[0], gold.data[1])
