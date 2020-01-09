import os
from geoparser import Document
from nlptools import SpacyNLP

class SpacyServer:

  def __init__(self):
    self.nlp = SpacyNLP()

  def get(self):
    return 'txt2map stand-alone NLP server'

  def post(self, req_text):
    doc = Document(req_text)
    self.nlp.annotate(doc)
    return doc.get_annotation_json()
