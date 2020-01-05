import requests
from .document import Document
from .matcher import NameMatcher
from .gazetteer import Gazetteer
from .config import Config

class ToponymRecognizer:

  def __init__(self, gazetteer):
    self.gaz = gazetteer
    self.matcher = NameMatcher(['num','stp','per'], 2) # 2 for US, UK, ...

  def parse(self, text):
    doc = Document(text)

    # annotate using NLP
    response = requests.post(url='http://localhost:81', data=text)
    response.encoding = 'utf-8'
    doc.import_json(response.text)

    # annotate using gazetteer
    self.matcher.recognize_names(doc, 'gaz', self.gaz.lookup_prefix)

    doc.clear_overlaps('rec')
    return doc

