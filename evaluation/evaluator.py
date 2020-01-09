from geoparser import GeoNamesCache, OSMLoader, GeoUtil

class Evaluator:

  def __init__(self, strict=True, recog=True, resol=True, tolerance_global=161, tolerance_local=1):
    self.strict = strict
    self.recog = recog
    self.resol = resol
    self.tol_global = tolerance_global
    self.tol_local = tolerance_local
    self.gns_cache = GeoNamesCache()

    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0

    self.accurate = 0
    self.inaccurate = 0
    self.missed = 0

  def evaluate(self, doc, gold_doc):
    if self.recog:
      self._evaluate_rec(doc, gold_doc)
    if self.resol:
      self._evaluate_res(doc, gold_doc)

  def _evaluate_rec(self, doc, gold_doc):
    true_positives = []
    false_positives = []
    false_negatives = []

    correct_indices = []

    for gold in gold_doc.get_all('rec'):
      anns = doc.get(gold.pos)

      if 'rec' in anns:
        ann = anns['rec']
        recognized = self._matches_phrase(ann, gold)
      else:
        cluster_anns = [a for l, a in anns.items() if l.startswith('clu-')]
        recognized = False
        for a in cluster_anns:
          recognized = self._matches_phrase(a, gold)
          if recognized:
            ann = a
            break
          
      if recognized:
        correct_indices += list(range(ann.pos, ann.end_pos()))
        true_positives.append(gold)
      else:
        false_negatives.append(gold)

    for rec_ann in doc.get_all('res'): # local matches not counted
      if rec_ann.pos not in correct_indices:
        false_positives.append(rec_ann)

    self.true_pos += len(true_positives)
    self.false_pos += len(false_positives)
    self.false_neg += len(false_negatives)

    self._print_if_not_empty(false_positives, 'REC FALSE POS')
    self._print_if_not_empty(false_negatives, 'REC FALSE NEG')

  def _evaluate_res(self, doc, gold_doc):
    accurates = []
    inaccurates = []
    missed = []

    for gold in gold_doc.get_all('res'):
      anns = doc.get(gold.pos)
      
      if 'res' in anns:
        ann = anns['res']
        in_tolerance = self._global_res_in_tolerance(anns['res'], gold)
      elif 'wik' in anns:
        ann = anns['wik']
        in_tolerance = self._wiki_res_in_tolerance(anns['wik'], gold)
      else:
        cluster_anns = [a for l, a in anns.items() if l.startswith('clu-')]
        if len(cluster_anns) == 0:
          missed.append(gold)
          continue
        ann = cluster_anns[0]
        for a in cluster_anns:
          in_tolerance = self._local_res_in_tolerance(a, gold)
          if in_tolerance:
            ann = a
            break
      
      if not self._matches_phrase(ann, gold):
        missed.append(gold)
        continue

      if in_tolerance:
        accurates.append(gold)
      else:
        inaccurates.append(gold)

    self.missed += len(missed)
    self.inaccurate += len(inaccurates)
    self.accurate += len(accurates)

    self._print_if_not_empty(missed, 'RES MISSED')
    self._print_if_not_empty(inaccurates, 'RES INACC')

  def _matches_phrase(self, a, gold):
    if not self.strict:
      return True
    elif a.phrase == gold.phrase:
      return True
    elif a.phrase + '.' == gold.phrase:
      return True
    return False

  def print_metrics(self):
    if self.recog:
      recognized = self.true_pos + self.false_pos
      if recognized > 0:
        p = self.true_pos / recognized
      else:
        p = 1.0
      xyz = self.true_pos + self.false_neg
      if xyz > 0:
        r = self.true_pos / xyz
      else:
        r = 1.0
      if self.true_pos > 0:
        f1 = (2 * p * r) / (p + r)
      else:
        f1 = 0.0
      print(f'P: {p:.3f} R: {r:.3f} F1: {f1:.3f}')

    if self.resol:
      total = self.accurate + self.inaccurate + self.missed
      if total > 0:
        acc = self.accurate / total
        not_missed = total - self.missed
        if not_missed > 0:
          acc_r = self.accurate / not_missed
        else:
          acc_r = 1.0
      else:
        acc = acc_r = 1.0
      tg = self.tol_global
      tl = self.tol_local
      print(f'Acc<{tg}/{tl}>: {acc:.3f} ({acc_r:.3f} of recognized)')

  def _print_if_not_empty(self, anns, msg):
    if len(anns) == 0:
      return
    names = [a.phrase for a in anns]
    print(f'{msg}: {names}')

  def _wiki_res_in_tolerance(self, a, gold):
    coords = WikiUtil.coordinates_for_url(a.data)
    if len(coords) == 0:
      return False
    (gold_lat, gold_lon) = self._gold_coords(gold)
    for lat, lon in coords:
      dist = GeoUtil.distance(lat, lon, gold_lat, gold_lon)
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
