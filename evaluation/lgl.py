import os
import logging
import csv
import json
import datetime
from io import StringIO
from lxml import etree
from geoparser import Geoparser
from .evaluator import Annotation, CorpusEvaluator

class LGLEvaluator:

  def __init__(self):
    dirname = os.path.dirname(__file__)
    corpus_file = dirname + '/corpora/lgl.xml'
    tree = etree.parse(corpus_file)
    self.articles = tree.getroot()

    self.parser = Geoparser()
    self.eval = CorpusEvaluator(self.parser)

  def test_all(self, save_report=True, doc_range=range(200)):
    for i in doc_range:
      self.test(i, False)
      
    logging.info(f'--- FINISHED ---')
    summary = self.eval.corpus_summary(161)
    logging.info('Overall: %s', summary)

    if not save_report:
      return

    csv_str = self.eval.results_csv()
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H%M')
    file_name = f'eval-lgl-{now}.csv'
    with open(file_name, mode='w', encoding='utf-8') as f:
      f.write(csv_str)
    logging.info('wrote results to ' + file_name)

  def test(self, doc_idx, print_report=True):
    article = self.articles[doc_idx]
    doc_id = article.get('docid')
    text = article.find('text').text

    doc_name = f'LGL-{doc_id} [{doc_idx}]'
    self.eval.start_document(doc_name, text)

    toponyms = article.find('toponyms')

    for toponym in toponyms:
      tag = toponym.find('gaztag')
      if tag == None:
        continue

      position = int(toponym.find('start').text)
      name = toponym.find('phrase').text
      geoname_id = tag.get('geonameid')
      lat = float(tag.find('lat').text)
      lon = float(tag.find('lon').text)

      a = Annotation(position, name, lat, lon, geoname_id)
      self.eval.verify_annotation(a)

    summary = self.eval.document_summary(161)
    logging.info(summary)

    if print_report:
      print(self.eval.results_csv())
