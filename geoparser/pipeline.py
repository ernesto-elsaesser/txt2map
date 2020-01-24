
class Step:

  def annotate(self, doc):
    return

from .document import Layer
from .ner import SpacyEntityRecognizer, StanfordEntityRecognizer, CogCompEntityRecognizer, GCNLEntityLinker
from .reclassifier import Reclassifier
from .localparser import LocalGeoparser
from .globalparser import GlobalGeoparser
from .gazetteer import Gazetteer
from .util import GeoUtil


class Pipeline:

  def __init__(self):
    self.steps = []

  def add(self, step):
    self.steps.append(step)

  def key_path(self):
    return [s.key for s in self.steps]

  def annotate(self, doc):
    for step in self.steps:
      step.annotate(doc)


class PipelineBuilder:

  spacy_url = None
  cogcomp_url = None
  stanford_url = None
  keep_defaults = False

  def build_empty(self):
    return Pipeline()

  def build_ner(self, ner_key):
    pipe = self.build_empty()
    if ner_key == SpacyEntityRecognizer.key:
      pipe.add(SpacyEntityRecognizer(self.spacy_url))
    elif ner_key == CogCompEntityRecognizer.key:
      pipe.add(CogCompEntityRecognizer(self.cogcomp_url))
    elif ner_key == StanfordEntityRecognizer.key:
      pipe.add(StanfordEntityRecognizer(self.stanford_url))
    elif ner_key == GCNLEntityLinker.key:
      pipe.add(GCNLEntityLinker())
      pipe.add(DemonymRemover())
    else:
      raise PipelineException('Invalid key for NER step!')
    return pipe

  def build_topo(self, ner_key):
    pipe = self.build_ner(ner_key)
    pipe.add(Reclassifier())
    return pipe

  def build_global(self, ner_key):
    pipe = self.build_topo(ner_key)
    pipe.add(GlobalGeoparser(self.keep_defaults))
    return pipe

  def build(self, ner_key):
    pipe = self.build_global(ner_key)
    pipe.add(LocalGeoparser())
    return pipe

  def build_wiki(self):
    pipe = self.build_empty()
    pipe.add(GCNLEntityLinker())
    pipe.add(WikiResolver())
    return pipe
  

class WikiResolver(Step):

  key = 'wikires'
  layers = [Layer.lres]

  def annotate(self, doc):
    wiki_anns = doc.annotations_by_position(Layer.wiki)
    for a in doc.get_all(Layer.ner, 'loc'):
      if a.pos not in wiki_anns:
        continue
      url = wiki_anns[a.pos].data
      (lat, lon) = GeoUtil.coordinate_for_wiki_url(wiki_url)
      data = [lat, lon, url]
      doc.annotate(Layer.lres, a.pos, a.phrase, 'wiki', data)


class DemonymRemover(Step):

  key = 'remdem'
  layers = [Layer.ner]

  def __init__(self):
    dem_map = Gazetteer.demonyms()
    self.demonyms = sum(dem_map.values(), [])

  def annotate(self, doc):
    for a in doc.get_all(Layer.ner):
      if a.group == 'loc' and a.phrase in self.demonyms:
        doc.delete_annotation(Layer.ner, a.pos)
