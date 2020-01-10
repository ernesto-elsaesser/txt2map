import os
from annotation import Document, PipelineBuilder

class SpacyServer:

  def __init__(self):
    builder = PipelineBuilder()
    self.pipe = builder.build_no_loc('spacy')

  def get(self):
    return 'txt2map spaCy NLP server'

  def post(self, req_text):
    doc = Document(req_text)
    self.pipe.annotate(doc)
    return doc.export_layers()
