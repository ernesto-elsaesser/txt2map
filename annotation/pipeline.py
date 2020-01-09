from geoparser import GazetteerRecognizer, GeoNamesResolver, Clusterer
from .spacy import SpacyNLP, SpacyClient
from .gcnl import GoogleCloudNL
from .cogcomp import CogCompClient


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

  @staticmethod
  def spacy(port=8001, use_gazetteer=True, global_resol=True, local_resol=True):
    pipe = Pipeline()
    pipe.add(SpacyServerStep(port))
    pipe.add(LocationRecogStep())
    if use_gazetteer:
      pipe.add(GazetteerRecogStep())
    if global_resol:
      pipe.add(GeoNamesRecogResolStep())
      if local_resol:
        pipe.add(ClusterStep())
    return pipe

  @staticmethod
  def cogcomp(port=8002, use_gazetteer=True, global_resol=True, local_resol=True):
    pipe = Pipeline()
    pipe.add(SpacyTokenStep())
    pipe.add(CogCompServerStep(port))
    pipe.add(LocationRecogStep())
    if use_gazetteer:
      pipe.add(GazetteerRecogStep())
    if global_resol:
      pipe.add(GeoNamesRecogResolStep())
      if local_resol:
        pipe.add(ClusterStep())
    return pipe

  @staticmethod
  def gcnl(use_gazetteer=True, global_resol=True, local_resol=True):
    pipe = Pipeline()
    pipe.add(SpacyTokenStep())
    pipe.add(GCNLStep())
    pipe.add(LocationRecogStep())
    if use_gazetteer:
      pipe.add(GazetteerRecogStep())
    if global_resol:
      pipe.add(GeoNamesRecogResolStep())
      if local_resol:
        pipe.add(ClusterStep())
    return pipe
    

class SpacyTokenStep:

  key = 'tok'

  def __init__(self):
    self.spacy = SpacyNLP(False)

  def annotate(self, doc):
    self.spacy.annotate_ntk(doc)
    return ['ntk']


class SpacyServerStep:

  key = 'spacy'

  def __init__(self, port):
    self.spacy = SpacyClient(port)

  def annotate(self, doc):
    self.spacy.annotate_ntk_ner(doc)
    return ['ntk', 'ner']


class SpacyStep:

  key = 'spacy'

  def __init__(self):
    self.spacy_sm = SpacyNLP(False)
    self.spacy_lg = SpacyNLP(True)

  def annotate(self, doc):
    self.spacy_sm.annotate_ntk(doc)
    self.spacy_lg.annotate_ner(doc)
    self.spacy_sm.annotate_ner(doc)
    return ['ntk', 'ner']


class CogCompServerStep:

  key = 'cogcomp'

  def __init__(self, port):
    self.cogcomp = CogCompClient(port)

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


class GCNLStep:

  key = 'gcnl'

  def __init__(self):
    self.gncl = GoogleCloudNL()

  def annotate(self, doc):
    self.gncl.annotate_ner_wik(doc)
    return ['ner', 'wik']

