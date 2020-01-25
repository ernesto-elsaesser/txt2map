
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .gazetteer import Gazetteer

class Reclassifier(Step):

  key = 'topo'
  layers = [Layer.topo]

  def __init__(self):
    self.toponyms = set(Gazetteer.large_entries())

  def annotate(self, doc):
    for a in doc.get_all(Layer.ner, 'loc'):
      print(f'topo - using LOC: {a.phrase}')
      doc.annotate(Layer.topo, a.pos, a.phrase, 'orig', a.phrase)

    #for a in doc.get_all(Layer.ner, 'per'):
    #  if a.phrase in self.toponyms:
    #    print(f'topo - using PER: {a.phrase}')
    #    doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)

    for a in doc.get_all(Layer.ner, 'org'):
      if self._is_toponym(doc, a):
        print(f'topo - using ORG: {a.phrase}')
        doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)

    for a in doc.get_all(Layer.ner, 'fac'):
      if self._is_toponym(doc, a):
        print(f'topo - using FAC: {a.phrase}')
        doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)

  def _is_toponym(self, doc, ann):
    if ann.phrase not in self.toponyms:
      return False
    end = ann.end_pos()
    if doc.text[end] == ' ' and doc.text[end+1].isupper():
      return False
    return True
    
