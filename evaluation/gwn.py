import os
import logging
import csv
import json
import datetime
from geoparser import Geoparser, Document
from .evaluator import GoldAnnotation, CorpusEvaluator

class GeoWebNewsEvaluator:

  non_topo_types = ["Non_Toponym", "Non_Lit_Expression", "Literal_Expression"]
  rec_only_types = ["Demonym", "Homonym", "Language"]

  def __init__(self, incl_rec_only=False, incl_hard=False, keep_defaults=False, count_inexact=True):
    self.no_rec = not incl_rec_only
    self.no_hard = not incl_hard
    self.keep_defaults = keep_defaults

    dirname = os.path.dirname(__file__)
    self.corpus_dir = dirname + '/corpora/GeoWebNews/'
    self.results_dir = dirname + '/results/GeoWebNews'
    paths = os.listdir(self.corpus_dir)
    docs = [p.replace('.txt', '') for p in paths if p.endswith('.txt')]
    self.docs = list(sorted(docs, key=lambda s: int(s)))

    self.parser = Geoparser()
    self.eval = CorpusEvaluator(count_inexact, 161)

  def test_all(self, doc_range=range(200)):
    for i in doc_range:
      self.test(i, False)

    logging.info('--- RESULTS ---')
    logging.info(self.eval.metrics_str())

  def test(self, doc_idx, print_metrics=True):
    doc_id = self.docs[doc_idx]
    logging.info(f'--- GWN-{doc_id} [{doc_idx}] ---')

    text_path = self.corpus_dir + doc_id + '.txt'
    with open(text_path, encoding='utf-8') as f:
      text = f.read()

    result_path = f'{self.results_dir}/{doc_id}.json'
    if os.path.exists(result_path):
      doc = Document(text)
      doc.load_annotations(result_path)
    else:
      doc = self.parser.parse(text, self.keep_defaults)
      doc.save_annotations(result_path)

    self.eval.start_document(doc, self.parser)

    annotation_path = self.corpus_dir + doc_id + '.ann'
    with open(annotation_path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')

      incomplete = {}
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT token
          ann_type = data[0]
          if ann_type in self.non_topo_types:
            continue
          if self.no_rec and ann_type in self.rec_only_types:
            continue
          position = int(data[1])
          name = row[2]
          incomplete[tag_id] = GoldAnnotation(position, name, 0, 0, None)

        elif tag_id.startswith('#'):  # BRAT annotator note
          tag_id = data[1]
          if tag_id not in incomplete:
              continue

          a = incomplete[tag_id]
          if ',' in row[2]:
            if self.no_hard:
              continue
            coords = row[2].split(',')
            a.lat = float(coords[0].strip())
            a.lon = float(coords[1].strip())
          elif row[2] != 'N/A':
            geoname_id = int(row[2])
            geoname = self.parser.gns_cache.get(geoname_id)
            a.geoname_id = geoname_id
            a.lat = geoname.lat
            a.lon = geoname.lon

          self.eval.evaluate(a)

    if print_metrics:
      logging.info(self.eval.metrics_str())
