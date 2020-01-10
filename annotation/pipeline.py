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


class PipelineBuilder:

  def __init__(self, spacy_port=8001, cogcomp_port=8002):
    self.spacy_port = spacy_port
    self.cogcomp_port = cogcomp_port

  def build_no_loc(self, ner_key):
    pipe = Pipeline()
    if ner_key == SpacyServerStep.key:
      pipe.add(SpacyServerStep(self.spacy_port))
    else:
      pipe.add(SpacyTokenStep())
      if ner_key == CogCompServerStep.key:
        pipe.add(CogCompServerStep(self.cogcomp_port))
      elif ner_key == GCNLStep.key:
        pipe.add(GCNLStep())
      else:
        raise Exception('Invalid key for NER step!')
    return pipe

  def build_no_gaz(self, ner_key):
    pipe = self.build_no_loc(ner_key)
    pipe.add(LocationRecogStep())
    return pipe

  def build_no_glob(self, ner_key):
    pipe = self.build_no_gaz(ner_key)
    pipe.add(GazetteerRecogStep())
    return pipe

  def build_no_clust(self, ner_key):
    pipe = self.build_no_glob(ner_key)
    pipe.add(GeoNamesRecogResolStep())
    return pipe

  def build(self, ner_key):
    pipe = self.build_no_clust(ner_key)
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

