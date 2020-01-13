from geoparser import GazetteerRecognizer, GeoNamesResolver, Clusterer, GeoUtil
from .spacy import SpacyClient
from .gcnl import GoogleCloudNL
from .cogcomp import CogCompClient
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

  def __init__(self, spacy_url=None, cogcomp_url=None):
    self.spacy_url = spacy_url
    self.cogcomp_url = cogcomp_url

  def build_ner(self, ner_key):
    pipe = Pipeline()
    if ner_key == SpacyServerNERStep.key:
      pipe.add(SpacyServerNERStep(self.spacy_url))
    elif ner_key == CogCompServerNERStep.key:
      pipe.add(CogCompServerNERStep(self.cogcomp_url))
    elif ner_key == GCNLNERStep.key:
      pipe.add(GCNLNERStep())
    else:
      raise PipelineException('Invalid key for NER step!')
    return pipe

  def build_loc(self, ner_key):
    pipe = self.build_ner(ner_key)
    pipe.add(LocationRecogStep())
    return pipe

  def build_gaz(self, ner_key):
    pipe = self.build_loc(ner_key)
    pipe.add(GazetteerRecogStep())
    return pipe

  def build_glob(self, ner_key):
    pipe = self.build_gaz(ner_key)
    pipe.add(GeoNamesRecogResolStep())
    return pipe

  def build(self, ner_key):
    pipe = self.build_glob(ner_key)
    pipe.add(ClusterStep())
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


class LocationRecogStep:

  key = 'loc'

  def annotate(self, doc):
    for a in doc.get_all('ner', 'loc'):
      doc.annotate('rec', a.pos, a.phrase, 'ner', a.phrase)
    return ['rec']


class GazetteerRecogStep:

  key = 'gaz'

  def __init__(self):
    self.gazrec = GazetteerRecognizer()

  def annotate(self, doc):
    self.gazrec.annotate_rec(doc)
    return ['rec']


class GeoNamesRecogResolStep:

  key = 'geores'

  def __init__(self):
    self.geores = GeoNamesResolver()

  def annotate(self, doc):
    self.geores.annotate_rec_res(doc)
    return ['rec', 'res']


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
    layers = self.clusterer.annotate_clu(doc)
    layers.append('clu')
    return layers


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
    self.gncl = GoogleCloudNL()

  def annotate(self, doc):
    self.gncl.annotate_ner_wik(doc)
    return ['ner', 'wik']


class WikiResolStep:

  key = 'wiki'

  def annotate(self, doc):
    wik_anns = doc.annotations_by_index('wik')
    for a in doc.get_all('ner', 'loc'):
      if a.pos not in wik_anns:
        continue
      url = wik_anns[a.pos].data
      coords = GeoUtil.coordinates_for_wiki_url(url)
      if len(coords) > 0:
        doc.annotate('res', a.pos, a.phrase, 'wik', coords)
    return ['res']
