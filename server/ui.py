import os
from annotation import Document


class UIServer:

  def __init__(self, pipeline):
    self.pipe = pipeline
    dirname = os.path.dirname(__file__)
    self.index_path = dirname + '/index.html'

  def get(self):
    with open(self.index_path, 'rb') as f:
      return f.read()

  def post(self, req_text):
    doc = Document(text=req_text)
    self.pipe.annotate(doc)
    return doc.export_layers()

