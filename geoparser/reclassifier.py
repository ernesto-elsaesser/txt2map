
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .gazetteer import Gazetteer

class Reclassifier(Step):

  key = 'topo'
  layers = [Layer.topo]

  def __init__(self):
    self.toponyms = set()
    self.toponyms.update(Gazetteer.admins())
    self.toponyms.update(Gazetteer.cities())

  def annotate(self, doc):
    for a in doc.get_all(Layer.ner, 'loc'):
      print(f'topo - using LOC: {a.phrase}')
      doc.annotate(Layer.topo, a.pos, a.phrase, 'orig', a.phrase)

    for a in doc.get_all(Layer.ner, 'per'):
      if a.phrase in self.toponyms:
        print(f'topo - using PER: {a.phrase}')
        doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)

    for a in doc.get_all(Layer.ner, 'org'):
      if a.phrase in self.toponyms:
        print(f'topo - using ORG: {a.phrase}')
        doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)
