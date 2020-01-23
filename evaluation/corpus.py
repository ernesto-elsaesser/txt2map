import os
from geoparser import Document

class Corpus:

  def __init__(self, corpus_name):
    self.corpus_name = corpus_name
    dirname = os.path.dirname(__file__)
    data_dir = f'{dirname}/data'
    if not os.path.exists(data_dir):
      os.mkdir(data_dir)
    self.corpus_dir = f'{data_dir}/{corpus_name}'
    self.text_dir = f'{self.corpus_dir}/text'
    if not os.path.exists(self.corpus_dir):
      os.mkdir(self.corpus_dir)
    if not os.path.exists(self.text_dir):
      os.mkdir(self.text_dir)

  def document_ids(self):
    paths = os.listdir(self.text_dir)
    return [p.replace('.txt', '') for p in paths]

  def add_document(self, doc_id, gold_doc):
    text_path = self._text_path(doc_id)
    with open(text_path, 'w') as f:
      f.write(gold_doc.text)
    self.annotate_document(doc_id, ['gold'], gold_doc)

  def get_gold_document(self, doc_id):
    return self.get_document(doc_id, ['gold'])

  def annotate_document(self, doc_id, key_path, doc):
    ann_path = self._annotations_path(key_path, doc_id)
    json_str = doc.export_layers()
    with open(ann_path, 'w') as f:
      f.write(json_str)

  def get_document(self, doc_id, key_path):
    text_path = self._text_path(doc_id)
    with open(text_path, 'r') as f:
      text = f.read()
    doc = Document(text)

    ann_path = self._annotations_path(key_path, doc_id)
    with open(ann_path, 'r') as f:
      json_str = f.read()
    doc.import_layers(json_str)

    return doc

  def process(self, pipeline, doc_id, saved_steps=[]):
    doc = self.get_document(doc_id, saved_steps)
    key_path = []
    for step in pipeline.steps:
      key_path.append(step.key)
      if step.key not in saved_steps:
        layers = step.annotate(doc)
        self.annotate_document(doc_id, key_path, doc, layers)
    return doc

  def bulk_process(self, pipeline, saved_steps=[], doc_range=None, evaluator=None):
    doc_ids = self.document_ids()
    num_docs = len(doc_ids)
    doc_range = doc_range or range(num_docs)

    for i in doc_range:
      doc_id = doc_ids[i]
      print(f'-- {doc_id} ({i+1}/{num_docs}) --')
      doc = self.process(pipeline, doc_id, saved_steps)

      if evaluator != None:
        gold_doc = self.get_gold_document(doc_id)
        evaluator.evaluate(doc, gold_doc)

    if evaluator != None:
      print(f'-- EVALUATION --')
      evaluator.print_metrics()

  def _annotations_path(self, key_path, doc_id):
    key_str = '-'.join(key_path)
    ann_dir = f'{self.corpus_dir}/{key_str}'
    if not os.path.exists(ann_dir):
      os.mkdir(ann_dir)
    ann_path = f'{ann_dir}/{doc_id}.json'
    return ann_path

  def _text_path(self, doc_id):
    return f'{self.text_dir}/{doc_id}.txt'


