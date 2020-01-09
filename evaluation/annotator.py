import requests
from .store import DocumentStore
from geoparser import Geoparser, Config
from nlptools import SpacyNLP, GoogleCloudNL, CogCompNLP


class SpacyAnnotator:

  key = 'spacy'

  def __init__(self, use_server):
    self.use_server = use_server
    if not use_server:
      self.spacy = SpacyNLP()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)

    if self.use_server:
      body = doc.text().encode('utf-8')
      response = requests.post(url='http://localhost:8001', data=body)
      response.encoding = 'utf-8'
      doc.set_annotation_json(response.text)
    else:
      self.spacy.annotate(doc)

    return doc


class CogCompAnnotator:

  key = 'cogcomp'

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)

    text = doc.text()
    esc_text = text.replace('[', '{').replace(']', '}')
    body = esc_text.encode('utf-8')
    response = requests.post(url='http://localhost:8002', data=body)
    response.encoding = 'utf-8'

    CogCompNLP.import_annotations(doc, response.text)

    return doc


class GCNLAnnotator:

  key = 'gcnl'

  def __init__(self):
    self.gncl = GoogleCloudNL()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)
    self.gncl.annotate(doc)
    return doc


class T2MAnnotator:

  def __init__(self, ner_key, keep_defaults=False):
    self.ner_key = ner_key
    self.keep_defaults = keep_defaults
    key_suffix = '-def' if keep_defaults else ''
    self.onto_sim_rounds = 0 if keep_defaults else 5
    self.key = f'{ner_key}-txt2map{key_suffix}'
    self.geoparser = Geoparser()

  def annotate(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, self.ner_key)
    doc.delete_layer('rec')
    doc.delete_layer('res')

    if self.ner_key != 'spacy':
      spacy_doc = DocumentStore.load_doc(corpus_name, doc_id, 'spacy')
      spacy_anns = spacy_doc.get_annotation_json()
      doc.add_annotation_json(spacy_anns, 'ntk')

    Config.resol_max_onto_sim_rounds = self.onto_sim_rounds
    self.geoparser.annotate(doc)
    return doc
