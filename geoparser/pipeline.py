from .ner import SpacyClient, StanfordClient, CogCompClient, GoogleCloudNLClient
from .reclassifier import Reclassifier
from .local-parser import LocalGeoparser
from .global-parser import GlobalGeoparser
from .gazetteer import Gazetteer


class Step:

  def annotate(self, doc):
    return


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

  def build_empty(self):
    return Pipeline()

  def build_ner(self, ner_key):
    pipe = self.build_empty()
    if ner_key == SpacyServerNERStep.key:
      pipe.add(SpacyEntityRecognizer(self.spacy_url))
    elif ner_key == CogCompServerNERStep.key:
      pipe.add(CogCompEntityRecognizer(self.cogcomp_url))
    elif ner_key == StanfordServerNERStep.key:
      pipe.add(StanfordEntityRecognizer(self.stanford_url))
    elif ner_key == GCNLNERStep.key:
      pipe.add(GCNLEntityLinker())
      pipe.add(DemonymRemover())
    else:
      raise PipelineException('Invalid key for NER step!')
    return pipe

  def build_rec(self, ner_key):
    pipe = self.build_ner(ner_key)
    pipe.add(Reclassifier())
    return pipe

  def build_res(self, ner_key):
    pipe = self.build_rec(ner_key)
    pipe.add(GlobalGeoparser())
    return pipe

  def build(self, ner_key):
    pipe = self.build_res(ner_key)
    pipe.add(LocalGeoparser())
    return pipe

  def build_wiki(self):
    pipe = self.build_empty()
    pipe.add(GCNLEntityLinker())
    pipe.add(WikiResolver())
    return pipe
  




class GazetteerRecogStep(Step):

  key = 'gaz'

  def __init__(self):
    self.gazrec = GazetteerRecognizer()

  def annotate(self, doc):
    self.gazrec.annotate_rec(doc)
    return ['rec']


class GeoNamesRecogResolStep(Step):

  key = 'geores'

  def __init__(self):
    self.geores = GeoNamesResolver()

  def annotate(self, doc):
    self.geores.annotate_res(doc)
    return ['res']


class GeoNamesDefaultRecogResolStep(Step):

  key = 'georesdef'

  def __init__(self):
    self.geores = GeoNamesResolver(keep_defaults=True)

  def annotate(self, doc):
    self.geores.annotate_rec_res(doc)
    return ['rec', 'res']



class WikiResolver(Step):

  key = 'wikires'

  def annotate(self, doc):
    wik_anns = doc.annotations_by_position('wik')
    cache = {}
    for a in doc.get_all('ner', 'loc'):
      if a.pos not in wik_anns:
        continue
      url = wik_anns[a.pos].data
      doc.annotate('rec', a.pos, a.phrase, 'wik', '')
      doc.annotate('res', a.pos, a.phrase, 'wik', url)
    return ['rec','res']



class DemonymRemover(Step):

  key = 'remdem'
  layers = ['ner']

  def __init__(self):
    dem_map = Gazetteer.demonyms()
    self.demonyms = sum(dem_map.values(), [])

  def annotate(self, doc):
    for a in doc.get_all('ner'):
      if a.group == 'loc' and a.phrase in self.demonyms:
        doc.delete_annotation('ner', a.pos)
