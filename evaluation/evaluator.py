from geoparser import GeoNamesCache, OSMLoader, GeoUtil

class Evaluator:

  def __init__(self, strict=True, recog=True, resol=True, tolerance_global=161, tolerance_local=1):
    self.strict = strict
    self.recog = recog
    self.resol = resol
    self.tol_global = tolerance_global
    self.tol_local = tolerance_local
    self.gns_cache = GeoNamesCache()

    self.gold_rec_count = 0
    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0

    self.gold_res_count = 0
    self.accurate = 0
    self.inaccurate = 0

  def evaluate(self, doc, gold_doc):
    if self.recog:
      self._evaluate_rec(doc, gold_doc)
    if self.resol:
      self._evaluate_res(doc, gold_doc)

  def _evaluate_rec(self, doc, gold_doc):
    true_positives = []
    false_positives = []
    false_negatives = []

    anns = doc.annotations_by_position('rec')
    golds = gold_doc.get_all('rec')

    for gold in golds:
      recognized = False
      if gold.pos in anns:
        rec_ann = anns[gold.pos]
        if not self.strict:
          recognized = True
        elif rec_ann.phrase == gold.phrase:
          recognized = True
        elif rec_ann.phrase + '.' == gold.phrase:
          recognized = True
          
      if recognized:
        true_positives.append(gold)
      else:
        false_negatives.append(gold)

    correct_pos = [a.pos for a in true_positives]
    for rec_ann in anns.values():
      if rec_ann.pos not in correct_pos:
        false_positives.append(rec_ann)

    self.gold_rec_count += len(golds)
    self.true_pos += len(true_positives)
    self.false_pos += len(false_positives)
    self.false_neg += len(false_negatives)

    self._print_if_not_empty(false_positives, 'REC FALSE POS')
    self._print_if_not_empty(false_negatives, 'REC FALSE NEG')

  def _evaluate_res(self, doc, gold_doc):
    accurates = []
    inaccurates = []
    missed = []

    anns = doc.annotations_by_position('res')
    golds = gold_doc.get_all('res')

    for gold in golds:
      if gold.pos in anns:
        res_ann = anns[gold.pos]
        resolved = False

        if res_ann.group == 'wik':  # Wikipedia URL
          resolved = self._wiki_res_in_tolerance(res_ann, gold)
        elif res_ann.group.startswith('cl'):  # OpenStreetMap reference
          resolved = self._local_res_in_tolerance(res_ann, gold)
        else:  # GeoNames identifier
          resolved = self._global_res_in_tolerance(res_ann, gold)
            
        if resolved:
          accurates.append(gold)
        else:
          inaccurates.append(gold)

      else:
        missed.append(gold)

    self.gold_res_count += len(golds)
    self.inaccurate += len(inaccurates)
    self.accurate += len(accurates)

    self._print_if_not_empty(missed, 'RES MISSED')
    self._print_if_not_empty(inaccurates, 'RES INACC')

  def print_metrics(self):
    if self.recog:
      if self.gold_rec_count == 0:
        p = r = f1 = 1.0
      elif self.true_pos == 0:
        p = r = f1 = 0.0
      else:
        p = self.true_pos / (self.true_pos + self.false_pos)
        r = self.true_pos / (self.true_pos + self.false_neg)
        f1 = (2 * p * r) / (p + r)
      print(f'P: {p:.3f} R: {r:.3f} F1: {f1:.3f}')

    if self.resol:
      not_missed = self.accurate + self.inaccurate
      if self.gold_res_count == 0:
        acc = acc_r = 1.0
      elif not_missed == 0:
        acc = self.accurate / self.gold_res_count
        acc_r = 0.0
      else:
        acc = self.accurate / self.gold_res_count
        acc_r = self.accurate / (self.accurate + self.inaccurate)
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
