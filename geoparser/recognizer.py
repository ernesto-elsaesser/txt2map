from .document import Document
from .matcher import NameMatcher
from .gazetteer import Gazetteer

class GazetteerRecognizer:

  def __init__(self):
    self.gaz = Gazetteer()
    self.matcher = NameMatcher()

  def annotate(self, doc):

    person_indicies = doc.annotations_by_index('ner', 'per')

    def validate(a, c):
      if a.pos in person_indicies:
        a_per = person_indicies[a.pos]
        if len(a_per.phrase) > len(c.match):
          return False
      l = len(c.match)
      if l in [2, 3] and c.match.isupper():
        return True # abbreviations like 'US', 'UK', 'UAE'
      if a.group == 'til' and l > 3:
        return True
      return False

    self.matcher.recognize_names(doc, 'gaz', self.gaz.lookup_prefix, validate)
