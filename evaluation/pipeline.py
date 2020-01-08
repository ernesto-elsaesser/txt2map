import os
from .loader import DocumentLoader
from geoparser import Document, Geoparser
from nlptools import SpacyNLP, GoogleCloudNL


class Pipeline:

  def annotate_all(self, corpus_name):

    for i in range(200):
      document_name = ''
      doc = ''

      self.annotate(corpus_name, document_name, doc)


class GoldAnnotator(Annotator):

  def annotate(self, corpus_name, document_name, text, gold_annotations):
    DocumentLoader.save_text(corpus_name, document_name, text)
    
    doc = Document(text)
    for a in gold_annotations:
      if a.geoname_id != None:
        group = 'geo'
        data = a.geoname_id
      else:
        group = 'crd'
        data = [a.lat, a.lon]
      doc.annotate('gld', a.pos, a.phrase, )
      
    DocumentLoader.save_text(corpus_name, document_name, doc)


  def __repr__(self):
    return f'{self.phrase} @ {self.position} [{self.geoname_id}]'


class SpacyPipeline(Pipeline):

  def __init__(self):
    self.spacy = SpacyNLP()
    super().__init__('spacy')

  def process(self, corpus_name, document_name, text):
    doc = Document(text)
    self.spacy.annotate(doc)
    self.loader.save(corpus_name, document_name, doc)


class SpacyGeoPipeline(Pipeline):

  def __init__(self):
    self.geoparser = Geoparser()
    self.spacy_loader = AnnotationLoader('spacy')
    super().__init__('spacy-geo')

  def make_doc(self, text):
    doc = self.spacy_loader.load
    self.spacy.annotate(doc)
    return doc

  def annotate(self, doc):
    self.spacy_loader.load
    self.geoparser.annotate(doc)


class GCNLAnnotator(Annotator):

  def __init__(self, corpus_name):
    self.gncl = GoogleCloudNL()
    super().__init__(corpus_name, 'google', self._parse, False)

  def annotate(self, doc):
    self.gncl.annotate(doc)


