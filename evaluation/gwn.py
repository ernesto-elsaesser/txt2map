import os
import logging
import csv
import json
from .evaluator import CorpusEvaluator

class GeoWebNewsEvaluator:

  used_annotation_types = ['Literal']

  def __init__(self):
    self.eval = CorpusEvaluator(1)
    dirname = os.path.dirname(__file__)
    self.corpus_dir = dirname + '/corpora/GeoWebNews/'

  def start(self):
    self.eval.start_corpus('GeoWebNews')

  def test_all(self, max_documents=None):
    count = 1
    for path in os.listdir(self.corpus_dir):
      if max_documents != None and count > max_documents:
        return
      if path.endswith('.txt'):
        self.test(path.replace('.txt', ''))
        count += 1

  def test(self, doc_id):
    text_path = self.corpus_dir + doc_id + '.txt'
    with open(text_path, encoding='utf-8') as f:
      text = f.read()

    self.eval.start_document(doc_id, text)

    annotation_path = self.corpus_dir + doc_id + '.ann'
    with open(annotation_path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')

      tag_data = {}
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT token
          annotation_type = data[0]
          if annotation_type in self.used_annotation_types:
            position = int(data[1])
            name = row[2]
            tag_data[tag_id] = (position, name)

        elif tag_id.startswith('#'):  # BRAT annotator note
          tag_id = data[1]
          if tag_id not in tag_data:
              continue
            
          (pos, name) = tag_data[tag_id]
          if ',' in row[2]:
            coords = row[2].split(',')
            lat = float(coords[0].strip())
            lng = float(coords[1].strip())
            coord = (lat, lng)
          else:
            geoname_id = int(row[2])
            coord = self.eval.geoname_to_coordinate(geoname_id)

          self.eval.test_gold_coordinate(pos, name, coord)

    self.eval.finish_document()

  def finish(self):
    self.eval.finish_corpus()
