import requests
from .store import DocumentStore
from geoparser import GazetteerRecognizer, Geoparser, Config
from nlptools import SpacyNLP, SpacyClient, GoogleCloudNL, CogCompClient


class SpacyAnnotator:

  key = 'spacy'

  def __init__(self, port=None):
    self.port = port
    if port == None:
      self.spacy = SpacyNLP()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)
    if self.port != None:
      SpacyClient.annotate(doc, self.port)
    else:
      self.spacy.annotate(doc)
    return doc


class CogCompAnnotator:

  key = 'cogcomp'

  def __init__(self, port):
    self.port = port

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)
    CogCompClient.annotate(doc, self.port)
    return doc


class GCNLAnnotator:

  key = 'gcnl'

  def __init__(self):
    self.gncl = GoogleCloudNL()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)
    self.gncl.annotate(doc)
    return doc


class GazetteerAnnotator:

  def __init__(self, ner_key):
    self.ner_key = ner_key
    self.key = f'{ner_key}-gaz'
    self.gazrec = GazetteerRecognizer()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, self.ner_key)
    self.gazrec.annotate(doc)
    return doc


class T2MAnnotator:

  def __init__(self, ann_key, keep_defaults=False):
    self.ann_key = ann_key
    self.keep_defaults = keep_defaults
    key_suffix = '-def' if keep_defaults else ''
    self.onto_sim_rounds = 0 if keep_defaults else 5
    self.key = f'{ann_key}-txt2map{key_suffix}'
    self.geoparser = Geoparser()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, self.ann_key)
    doc.delete_layer('res') # GCNL adds res layer

    if 'spacy' not in self.ann_key:
      spacy_doc = DocumentStore.load_doc(corpus_name, doc_id, 'spacy')
      spacy_anns = spacy_doc.get_annotation_json()
      doc.add_annotation_json(spacy_anns, 'ntk')

    Config.resol_max_onto_sim_rounds = self.onto_sim_rounds
    self.geoparser.annotate(doc)
    return doc
