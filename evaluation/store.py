import os
from geoparser import Document

class DocumentStore:

  @staticmethod
  def text_dir(corpus_name):
    corpus_dir = DocumentStore._corpus_dir(corpus_name)
    text_dir = f'{corpus_dir}/text'
    if not os.path.exists(text_dir):
      os.mkdir(text_dir)
    return text_dir

  @staticmethod
  def pipeline_dir(corpus_name, pipeline_id):
    corpus_dir = DocumentStore._corpus_dir(corpus_name)
    pipe_dir = f'{corpus_dir}/{pipeline_id}'
    if not os.path.exists(pipe_dir):
      os.mkdir(pipe_dir)
    return pipe_dir

  @staticmethod
  def doc_ids(corpus_name):
    text_dir = DocumentStore.text_dir(corpus_name)
    paths = os.listdir(text_dir)
    return [p.replace('.txt', '') for p in paths]

  @staticmethod
  def save_text(corpus_name, doc_id, text):
    text_dir = DocumentStore.text_dir(corpus_name)
    text_path = f'{text_dir}/{doc_id}.txt'
    with open(text_path, 'w') as f:
      f.write(text)

  @staticmethod
  def save_annotations(corpus_name, doc_id, pipeline_id, doc):
    pipe_dir = DocumentStore.pipeline_dir(corpus_name, pipeline_id)
    ann_path = f'{pipe_dir}/{doc_id}.json'
    json_str = doc.get_annotation_json()
    with open(ann_path, 'w') as f:
      f.write(json_str)

  @staticmethod
  def load_doc(corpus_name, doc_id, pipeline_id=None):
    text_dir = DocumentStore.text_dir(corpus_name)
    text_path = f'{text_dir}/{doc_id}.txt'
    with open(text_path, 'r') as f:
      text = f.read()
    doc = Document(text)

    if pipeline_id != None:
      pipe_dir = DocumentStore.pipeline_dir(corpus_name, pipeline_id)
      ann_path = f'{pipe_dir}/{doc_id}.json'
      if os.path.exists(ann_path):
        with open(ann_path, 'r') as f:
          ann_json = f.read()
        doc.set_annotation_json(ann_json)

    return doc

  @staticmethod
  def _corpus_dir(corpus_name):
    dirname = os.path.dirname(__file__)
    corpus_dir = f'{dirname}/data/{corpus_name}'
    if not os.path.exists(corpus_dir):
      os.mkdir(corpus_dir)
    return corpus_dir
