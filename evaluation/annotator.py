import requests
from .store import DocumentStore
from geoparser import Geoparser, Config
from nlptools import SpacyNLP, GoogleCloudNL, CogCompNLP


class CorpusAnnotator:

  def __init__(self, corpus_name):
    self.corpus_name = corpus_name

  def annotate_all(self, pipe, doc_range=None):
    paths = DocumentStore.doc_ids(self.corpus_name)
    num_docs = len(paths)
    doc_range = doc_range or range(len(paths))

    print(f'---- START ANNOTATION: {pipe.id_} ----')
    for i in doc_range:
      doc_id = paths[i]
      print(f'-- {doc_id} ({i+1}/{num_docs}) --')
      m = self.annotate_one(pipe, doc_id)
    print(f'---- END ANNOTATION ----')

  def annotate_one(self, pipe, doc_id):
    doc = pipe.make_doc(self.corpus_name, doc_id)
    DocumentStore.save_annotations(self.corpus_name, doc_id, pipe.id_, doc)

  def annotate_bulk(self, bulk_pipe):
    text_dir = DocumentStore.text_dir(self.corpus_name)
    target_dir = DocumentStore.pipeline_dir(self.corpus_name, bulk_pipe.id_)
    bulk_pipe.annotate_bulk(text_dir, target_dir)

class SpacyPipeline:

  id_ = 'spacy'

  def __init__(self, use_server):
    self.use_server = use_server
    if not use_server:
      self.spacy = SpacyNLP()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)

    if self.use_server:
      body = doc.text().encode('utf-8')
      response = requests.post(url='http://localhost:8001', data=body)
      response.encoding = 'utf-8'
      doc.set_annotation_json(response.text)
    else:
      self.spacy.annotate(doc)

    return doc


class CogCompPipeline:

  id_ = 'cogcomp'

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)

    text = doc.text()
    esc_text = text.replace('[', '{').replace(']', '}')
    body = esc_text.encode('utf-8')
    response = requests.post(url='http://localhost:8002', data=body)
    response.encoding = 'utf-8'
    cc_text = response.text

    i = 0
    pos = 0
    ent_pos = None
    ent_group = None
    ent_phrase = None
    while i < l:
      c = cc_text[i]
      if c == '[':
        ent_pos = pos
        ent_phrase = ''
        if cc_text[i+1] == 'M':
          ent_group = 'msc'
          i += 6
        else:
          ent_group = cc_text[i+1:i+4].lower()
          i += 5
      elif c == ']':
        doc.annotate('ner', ent_pos, ent_phrase, ent_group, 'cogcomp_conll')
      else:
        if c == text[pos]:
          if ent_phrase != None:
            ent_phrase += c
          pos += 1
        i += 1


    doc.set_annotation_json(response.text)

    return doc


class GCNLPipeline:

  id_ = 'gcnl'

  def __init__(self):
    self.gncl = GoogleCloudNL()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id)
    self.gncl.annotate(doc)
    return doc


class SpacyT2MPipeline:

  id_ = 'spacy-txt2map'

  def __init__(self):
    self.geoparser = Geoparser()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, 'spacy')
    Config.resol_max_onto_sim_rounds = 5
    self.geoparser.annotate(doc)
    return doc


class SpacyDefaultsPipeline:

  id_ = 'spacy-defaults'

  def __init__(self):
    self.geoparser = Geoparser()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, 'spacy')
    Config.resol_max_onto_sim_rounds = 0
    self.geoparser.annotate(doc)
    return doc


class GCNLT2MPipeline:

  id_ = 'gncl-txt2map'

  def __init__(self):
    self.geoparser = Geoparser()

  def make_doc(self, corpus_name, doc_id):
    doc = DocumentStore.load_doc(corpus_name, doc_id, 'gcnl')
    doc.delete_layer('rec')
    doc.delete_layer('res')
    self.geoparser.annotate(doc)
    return doc
