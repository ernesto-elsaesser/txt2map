from geoparser import GeoNamesResolver, Clusterer
from .spacy import SpacyClient
from .gcnl import GoogleCloudNLClient
from .cogcomp import CogCompClient
from .stanford import StanfordClient
from .topores import TopoResolverClient
from .exception import PipelineException


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

  def __init__(self):
    self.spacy_url = None
    self.cogcomp_url = None
    self.topores_url = None
    self.stanford_url = None

  def build_empty(self):
    return Pipeline()

  def build_ner(self, ner_key):
    pipe = self.build_empty()
    if ner_key == SpacyServerNERStep.key:
      pipe.add(SpacyServerNERStep(self.spacy_url))
    elif ner_key == CogCompServerNERStep.key:
      pipe.add(CogCompServerNERStep(self.cogcomp_url))
    elif ner_key == StanfordServerNERStep.key:
      pipe.add(StanfordServerNERStep(self.stanford_url))
    elif ner_key == GCNLNERStep.key:
      pipe.add(GCNLNERStep())
    else:
      raise PipelineException('Invalid key for NER step!')
    return pipe

  def build(self, ner_key):
    pipe = self.build_ner(ner_key)
    pipe.add(GeoNamesRecogResolStep())
    pipe.add(ClusterStep())
    return pipe

  def build_wiki(self):
    pipe = self.build_ner(GCNLNERStep.key)
    pipe.add(WikiResolStep())
    return pipe

  def build_topo(self):
    pipe = self.build_empty()
    pipe.add(TopoResolverServerStep(self.topores_url))
    return pipe
  

class SpacyServerNERStep:

  key = 'spacy'

  def __init__(self, url):
    self.spacy = SpacyClient(url)

  def annotate(self, doc):
    self.spacy.annotate_ner(doc)
    return ['ner']


class CogCompServerNERStep:

  key = 'cogcomp'

  def __init__(self, url):
    self.cogcomp = CogCompClient(url)

  def annotate(self, doc):
    self.cogcomp.annotate_ner(doc)
    return ['ner']


class StanfordServerNERStep:

  key = 'stanford'

  def __init__(self, url):
    self.stanford = StanfordClient(url)

  def annotate(self, doc):
    self.stanford.annotate_ner(doc)
    return ['ner']


class GazetteerRecogStep:

  key = 'gaz'

  def __init__(self):
    self.gazrec = GazetteerRecognizer()

  def annotate(self, doc):
    self.gazrec.annotate_rec_evi(doc)
    return ['rec', 'evi']


class GeoNamesRecogResolStep:

  key = 'geores'

  def __init__(self):
    self.geores = GeoNamesResolver()

  def annotate(self, doc):
    self.geores.annotate_rec_evi_res(doc)
    return ['rec', 'evi', 'res']


class GeoNamesDefaultRecogResolStep:

  key = 'georesdef'

  def __init__(self):
    self.geores = GeoNamesResolver(keep_defaults=True)

  def annotate(self, doc):
    self.geores.annotate_rec_res(doc)
    return ['rec', 'res']



class ClusterStep:

  key = 'clust'

  def __init__(self):
    self.clusterer = Clusterer()

  def annotate(self, doc):
    self.clusterer.annotate_clu(doc)
    self.clusterer.annotate_rec_res(doc)
    return ['clu', 'rec', 'res']


class ClusterConfidenceStep:

  key = 'conf'

  def __init__(self):
    self.clusterer = Clusterer()

  def annotate(self, doc):
    self.clusterer.annotate_con(doc)
    return ['con']


class GCNLNERStep:

  key = 'gcnl'

  def __init__(self):
    self.gncl = GoogleCloudNLClient()

  def annotate(self, doc):
    self.gncl.annotate_ner_wik(doc)
    return ['ner', 'wik']


class WikiResolStep:

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
    return ['res']


class TopoResolverServerStep:

  key = 'topores'

  def __init__(self, url):
    self.topo = TopoResolverClient(url)

  def annotate(self, doc):
    self.topo.annotate_res(doc)
    return ['res']
  
