from .document import Layer
from .pipeline import Step
from .datastore import Datastore
from .gazetteer import Gazetteer
from .classifier import BinaryDecisionTreeClassifier

class Reclassifier(Step):

  key = 'topo'
  layers = [Layer.topo]

  classes = ['org', 'fac', 'per']

  def __init__(self):
    self.clf = BinaryDecisionTreeClassifier('entrecl')
    self.extractor = ReclassificationFeatureExtractor()

  def annotate(self, doc):
    for a in doc.get_all(Layer.ner, 'loc'):
      print(f'topo - kept {a}')
      doc.annotate(Layer.topo, a.pos, a.phrase, 'orig', a.phrase)
      toponyms.add(a.phrase)

    for a in doc.get_all(Layer.ner):
      if a.group in ['org', 'fac', 'per']:
        features = self.extractor.feature_vector(doc, ann)
        if self.clf.predict(features):
          print(f'topo - added {a}')
          doc.annotate(Layer.topo, a.pos, a.phrase, 'recl', a.phrase)
          toponyms.add(a.phrase)
  

class ReclassificationFeatureExtractor:

  def __init__(self):
    self.demonyms = set()
    for names in Gazetteer.demonyms().values():
      self.demonyms.update(names)

  def feature_vector(self, doc, ann):
    name = ann.phrase
    results = Datastore.search_geonames(name)
    has_results = len(results) != 0
    if has_results:
      top_result = results[0]
      top_is_city = top_result.is_city
      top_is_admin = top_result.is_admin
      top_is_country = top_result.is_country
      top_is_demo = name in self.demonyms
      top_above_10k = top_result.population > 10_000
      top_above_100k = top_result.population > 100_000
      top_above_1m = top_result.population > 1_000_000
      top_is_exact = top_result.name == name or top_result.toponym_name == name
    else:
      top_is_city = False
      top_is_admin = False
      top_is_country = False
      top_is_demo = False
      top_above_10k = False
      top_above_100k = False
      top_above_1m = False
      top_is_exact = False
    before_container = self._succeeded_by_comma_and_upper(doc, ann)
    before_name = self._succeeded_by_upper(doc, ann)
    after_prep = self._preceded_by_prep(doc, ann)
    return [has_results, top_is_city, top_is_admin, top_is_country, top_is_demo, top_above_10k, top_above_100k, 
            top_above_1m, top_is_exact, before_container, before_name, after_prep]

  def _succeeded_by_comma_and_upper(self, doc, ann):
    end = ann.end_pos()
    if len(doc.text) < end + 3:
      return False
    if doc.text[end:end+1] != ', ':
      return False
    return doc.text[end+2].isupper()

  def _succeeded_by_upper(self, doc, ann):
    end = ann.end_pos()
    if len(doc.text) < end + 2:
      return False
    if doc.text[end] != ' ':
      return False
    return doc.text[end+1].isupper()

  def _preceded_by_prep(self, doc, ann):
    start = ann.pos
    if start < 3:
      return False
    prev_two = doc.text[start-3:start-1]
    if prev_two in ['to','at','in','of']:
      return True
    if start < 5:
      return False
    return doc.text[start-5:start-1] == 'from'
