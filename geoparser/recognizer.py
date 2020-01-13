from .matcher import NameMatcher
from .gazetteer import Gazetteer

class GazetteerRecognizer:

  def __init__(self):
    self.matcher = NameMatcher()
    self.lookup_tree = {}
    for toponym in Gazetteer.defaults():
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

  def annotate_rec(self, doc):
    person_indicies = doc.annotations_by_index('ner', 'per')

    def commit_match(c):
      if c.pos in person_indicies:
        a_per = person_indicies[c.pos]
        if len(a_per.phrase) > len(c.match):
          return False
      doc.annotate('rec', c.pos, c.match, 'gaz', c.lookup_phrase)
      return True

    self.matcher.find_matches(doc, self.lookup_prefix, commit_match)

  def lookup_prefix(self, prefix):
    key = prefix[:2]
    if key not in self.lookup_tree:
      return []
    toponyms = self.lookup_tree[key]
    return [t for t in toponyms if t.startswith(prefix)]
