from geoparser import GeoNamesCache, OSMLoader, GeoUtil, WikiUtil

class Evaluator:

  def __init__(self, strict=True, rec_only=False, tolerance_global=161, tolerance_local=1):
    self.strict = strict
    self.rec_only = rec_only
    self.tol_global = tolerance_global
    self.tol_local = tolerance_local
    self.total = Measurement()
    self.gns_cache = GeoNamesCache()

  def evaluate(self, rec_anns, res_anns, gold_anns):
    result = Measurement()
    result.false_pos = len(rec_anns)
    result.ann_count = len(gold_anns)

    for gold in gold_anns:
      recognized = False
      if gold.pos in rec_anns:
        rec_ann = rec_anns[gold.pos]
        if self.strict:
          recognized = rec_ann.phrase == gold.phrase
        else:
          recognized = True

      if recognized:
        result.false_pos -= 1
        result.true_pos += 1
      else:
        result.false_neg += 1
        print(f'NOT RECOGNIZED: {gold}')
        continue

      if self.rec_only:
        return

      resolved_within = False
      if gold.pos in res_anns:
        res_ann = res_anns[gold.pos]
        
        if res_ann.group == 'wik': # Wikipedia URL
          resolved_within = self._wiki_res_in_tolerance(res_ann, gold)
        elif res_ann.group.startswith('cl'):  # OpenStreetMap reference
          resolved_within = self._local_res_in_tolerance(res_ann, gold)
        else:  # GeoNames identifier
          resolved_within = self._global_res_in_tolerance(res_ann, gold)
          
      if resolved_within:
        result.accurate += 1
      else:
        print(f'NOT RESOLVED: {gold}')

    self.total.add(result)
    return result

  def log_total(self):
    self.log(self.total)

  def log(self, m):
    if m.ann_count == 0:
      p = r = f1 = acc = acc_r = 1.0
    elif m.true_pos == 0:
      p = r = f1 = acc = acc_r = 0.0
    else:
      p = m.true_pos / (m.true_pos + m.false_pos)
      r = m.true_pos / (m.true_pos + m.false_neg)
      f1 = (2 * p * r) / (p + r)
      acc = m.accurate / m.ann_count
      acc_r = m.accurate / m.true_pos

    result = f'P: {p: .3f} R: {r: .3f} F1: {f1: .3f}'
    if not self.rec_only:
      tg = self.tol_global
      tl = self.tol_local
      result += f' Acc({tg}|{tl}): {acc:.3f} ({acc_r:.3f} resol only)'

    print(result)

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



class Measurement:

  def __init__(self):
    self.true_pos = 0
    self.false_neg = 0
    self.false_pos = 0
    self.ann_count = 0
    self.accurate = 0

  def add(self, m):
    self.true_pos += m.true_pos
    self.false_neg += m.false_neg
    self.false_pos += m.false_pos
    self.ann_count += m.ann_count
    self.accurate += m.accurate
