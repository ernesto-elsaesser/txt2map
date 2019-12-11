import os
import logging
import csv
import json
import datetime
from geoparser import Geoparser
from .evaluator import Annotation, CorpusEvaluator

class GeoWebNewsEvaluator:

  used_annotation_types = ['Literal']

  def __init__(self):
    dirname = os.path.dirname(__file__)
    self.corpus_dir = dirname + '/corpora/GeoWebNews/'
    paths = os.listdir(self.corpus_dir)
    docs = [p.replace('.txt', '') for p in paths if p.endswith('.txt')]
    self.docs = list(sorted(docs, key=lambda s: int(s)))

    self.parser = Geoparser(nlp_model=2)
    self.eval = CorpusEvaluator(self.parser)

  def test_all(self, save_report=True, doc_range=range(200)):
    try:
      for i in doc_range:
        self.test(i, False)
      logging.info(f'--- FINISHED ---')
    except:
      logging.warning(f'--- EXCEPTION ---')

    summary = self.eval.corpus_summary(161)
    logging.info('Overall: %s', summary)

    if not save_report:
      return

    csv_str = self.eval.results_csv()
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H:%M')
    file_name = f'eval-gwn-{now}.csv'
    with open(file_name, mode='w', encoding='utf-8') as f:
      f.write(csv_str)
    logging.info('wrote results to ' + file_name)

  def test(self, doc_idx, print_report=True):
    doc = self.docs[doc_idx]
    text_path = self.corpus_dir + doc + '.txt'
    with open(text_path, encoding='utf-8') as f:
      text = f.read()

    doc_name = f'GWN-{doc} [{doc_idx}]'
    self.eval.start_document(doc_name, text)

    annotation_path = self.corpus_dir + doc + '.ann'
    with open(annotation_path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')

      annotations = {}
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT toke
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

    if print_report:
      print(self.eval.results_csv())
