
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .gazetteer import Gazetteer

class Reclassifier(Step):

  key = 'reclass'
  layers = [Layer.topo]

  def __init__(self):
    self.cities = Gazetteer.cities()
    self.admins = Gazetteer.admins()

  def annotate(self, doc):
    for a in doc.get_all(Layer.ner, 'loc'):
      doc.annotate(Layer.topo, a.pos, a.phrase, 'orig', a.phrase)

    for a in doc.get_all(Layer.ner, 'per'):
      if a in self.cities or a in self.admins:
        doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)

    for a in doc.get_all(Layer.ner, 'org'):
      if a in self.cities or a in self.admins:
        doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)
