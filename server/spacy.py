import os
from annotation import Document, SpacyStep

class SpacyServer:

  def __init__(self):
    self.step = SpacyStep()

  def get(self):
    return 'txt2map spaCy NLP server'

  def post(self, req_text):
    doc = Document(req_text)
    self.step.annotate(doc)
    return doc.export_layers()
