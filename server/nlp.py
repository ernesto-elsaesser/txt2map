import os
from geoparser import SpacyNLP, Document

class NLPServer:

  def __init__(self):
    self.nlp = SpacyNLP()

  def get(self):
    return 'txt2map stand-alone NLP server'

  def post(self, req_text):
    doc = Document()
    doc.set_json(req_text)
    self.nlp.annotate(doc)
    return doc.get_json()
