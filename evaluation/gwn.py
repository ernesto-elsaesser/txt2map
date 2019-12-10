import os
import logging
import csv
import json
import datetime
from geoparser import Geoparser
from .evaluator import Annotation, CorpusEvaluator

class GeoWebNewsEvaluator:

  used_annotation_types = ['Literal']

  def __init__(self, verify_street_level):
    self.verify_street_level = verify_street_level
    dirname = os.path.dirname(__file__)
    self.corpus_dir = dirname + '/corpora/GeoWebNews/'
    search_dist = 15 if verify_street_level else 0
    self.parser = Geoparser(nlp_model=2, local_search_dist_km=search_dist)
    self.eval = CorpusEvaluator(self.parser)
    self.eval.start_corpus('GWN')

  def test_all(self, save_report=True, doc_range=range(200)):
    paths = os.listdir(self.corpus_dir)
    docs = [p.replace('.txt', '') for p in paths if p.endswith('.txt')]
    docs = list(sorted(docs))

    try:
      for i in doc_range:
        logging.info(f'= {i} =')
        self.test(docs[i])
    except:
      logging.warning(f'--- EXCEPTION ---')
      pass

    summary = self.eval.corpus_summary(161)
    logging.info(summary)

    if save_report:
      report = self.eval.report_csv()
      now = datetime.datetime.now().date()
      file_name = f'eval-gwn-{now}.csv'
      with open(file_name, mode='w', encoding='utf-8') as f:
        f.write(report)
      logging.info('wrote results to ' + file_name)

  def test(self, doc_id):
    text_path = self.corpus_dir + doc_id + '.txt'
    with open(text_path, encoding='utf-8') as f:
      text = f.read()

    self.eval.start_document(doc_id, text)

    annotation_path = self.corpus_dir + doc_id + '.ann'
    with open(annotation_path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')

      annotations = {}
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT token
          annotation_type = data[0]
          if annotation_type in self.used_annotation_types:
            position = int(data[1])
            name = row[2]
            annotations[tag_id] = Annotation(position, name, 0, 0)

        elif tag_id.startswith('#'):  # BRAT annotator note
          tag_id = data[1]
          if tag_id not in annotations:
              continue

          a = annotations[tag_id]
          if ',' in row[2]:
            if not self.verify_street_level:
              continue
            coords = row[2].split(',')
            a.lat = float(coords[0].strip())
            a.lng = float(coords[1].strip())
            a.remark = 'hard'
          else:
            geoname_id = int(row[2])
            geoname = self.parser.resolver.gns_cache.get(geoname_id)
            a.lat = geoname.lat
            a.lng = geoname.lng

          self.eval.verify_annotation(a)

    summary = self.eval.document_summary(161)
    logging.info(summary)
