from .document import Document
from .gazetteer import Gazetteer

class HybridRecognizer:

  def __init__(self, gazetteer, matcher):
    self.gaz = gazetteer
    self.matcher = matcher

  def annotate(self, doc):

    pers_pos = []
    for a in doc.get('ner'):
      if a.data in ['GPE', 'LOC']:
        doc.annotate('rec', a.pos, a.phrase, 'ner', a.phrase)
      elif a.data == 'PERSON' and a.group == 'spacy_lg':
        pers_pos += list(range(a.pos, a.end_pos()))

    def validate(a, c):
      if a.pos in pers_pos and ' ' not in c.match:
        return False
      l = len(c.match)
      if l in [2, 3] and c.match.isupper():
        return True # abbreviations like 'US', 'UK', 'UAE'
      if a.group == 'til' and l > 3:
        return True
      return False

    self.matcher.recognize_names(doc, 'gaz', self.gaz.lookup_prefix, validate)
