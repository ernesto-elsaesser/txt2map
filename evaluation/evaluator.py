from geoparser import GeoNamesCache, OSMLoader, GeoUtil
from .store import DocumentStore


class CorpusEvaluator:

  def __init__(self, corpus_name, strict, tolerance_km):
    self.corpus_name = corpus_name
    self.strict = strict
    self.tolerance = tolerance_km
    self.gns_cache = GeoNamesCache()

  def evaluate_all(self, pipeline_id, target_pipeline_id='gold'):
    paths = DocumentStore.doc_ids(self.corpus_name)
    num_docs = len(paths)
    total = Measurement()

    print(f'---- START EVALUATION: {pipeline_id} / {target_pipeline_id} ----')
    for i, doc_id in enumerate(paths):
      print(f'-- {doc_id} ({i}/{num_docs}) --')
      m = self.evaluate_one(doc_id, pipeline_id, target_pipeline_id)
      total.add(m)

    print(f'---- END EVALUATION ----')
    self._print_metrics(total)

  def evaluate_one(self, doc_id, pipeline_id, target_pipeline_id='gold'):
    doc = DocumentStore.load_doc(self.corpus_name, doc_id, pipeline_id)
    target_doc = DocumentStore.load_doc(self.corpus_name, doc_id, target_pipeline_id)

    rec_anns = doc.annotations_by_position('rec')
    res_anns = doc.annotations_by_position('res')
    gold_anns = target_doc.get('gld')

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

      resolved_within = False
      if gold.pos in res_anns:
        res_ann = res_anns[gold.pos]
        
        if not res_ann.group.startswith('cl'):  # global
          resolved_within = self._global_res_in_tolerance(res_ann, gold)
        else:  # local
          resolved_within = self._local_res_in_tolerance(res_ann, gold)
          
      if resolved_within:
        result.accurate += 1
      else:
        print(f'NOT RESOLVED: {gold}')

    self._print_metrics(result)
    return result

  def _global_res_in_tolerance(self, a, gold):
    if gold.data == a.data:
      return True
    g = self.gns_cache.get(a.data)
    (gold_lat, gold_lon) = self._gold_coords(gold)
    dist = GeoUtil.distance(g.lat, g.lon, gold_lat, gold_lon)
    return dist < self.tolerance

  def _local_res_in_tolerance(self, a, gold):
    elements = OSMLoader.load_geometries(a.data)
    (gold_lat, gold_lon) = self._gold_coords(gold)
    dist = GeoUtil.osm_element_distance(gold_lat, gold_lon, elements[0])
    if dist < self.tolerance:
      return True
    elif dist < self.tolerance + 30.0:  # max dist between two elements
      for e in elements[1:]:
        d = GeoUtil.osm_element_distance(gold_lat, gold_lon, e)
        if d < dist:
          return True
    return False

  def _gold_coords(self, gold):
    if gold.group == 'gns':
      g = self.gns_cache.get(gold.data)
      return (g.lat, g.lon)
    else:
      return (gold.data[0], gold.data[1])

  def _print_metrics(self, m):
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

    am = f'Acc@{self.tolerance:.1f}km'
    print(f'P: {p:.3f} R: {r:.3f} F1: {f1:.3f} {am}: {acc:.3f} ({acc_r:.3f} for resol only)')


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
