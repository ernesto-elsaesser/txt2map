import requests
from .store import DocumentStore
from geoparser import Geoparser
from nlptools import SpacyNLP, GoogleCloudNL


class CorpusAnnotator:

  def __init__(self, corpus_name):
    self.corpus_name = corpus_name

  def annotate_all(self, pipeline, doc_range=None):
    paths = DocumentStore.doc_ids(self.corpus_name)
    doc_range = doc_range or range(len(paths))

    print(f'---- START ANNOTATION: {pipeline.id_} ----')
    for i in doc_range:
      doc_id = paths[i]
      m = self.annotate_one(pipeline, doc_id)
    print(f'---- END ANNOTATION ----')

  def annotate_one(self, pipeline, doc_id):
    print(f'-- {doc_id} --')
    doc = pipeline.make_doc(self.corpus_name, doc_id)
    DocumentStore.save_annotations(self.corpus_name, doc_id, pipeline.id_, doc)


class Pipeline:

  id_ = ''


class SpacyPipeline(Pipeline):

  id_ = 'spacy'

  def __init__(self, use_server):
    self.use_server = use_server
    if not use_server:
      self.spacy = SpacyNLP()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)

    if self.use_server:
      response = requests.post(url='http://localhost:81', data=doc.text())
      response.encoding = 'utf-8'
      doc.set_annotation_json(response.text)
    else:
      self.spacy.annotate(doc)

    return doc


class GCNLPipeline(Pipeline):

  id_ = 'gcnl'

  def __init__(self):
    self.gncl = GoogleCloudNL()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)
    self.gncl.annotate(doc)


class SpacyT2MPipeline(Pipeline):

  id_ = 'spacy-txt2map'

  def __init__(self):
    self.geoparser = Geoparser()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, 'spacy')
    self.geoparser.annotate(doc)
    return doc


class GCNLT2MPipeline(Pipeline):

  id_ = 'gncl-txt2map'

  def __init__(self):
    self.geoparser = Geoparser()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, 'gcnl')
    doc.delete_layer('rec')
    doc.delete_layer('res')
    self.geoparser.annotate(doc)
    return doc



