from .matcher import NameMatcher
from .gazetteer import Gazetteer

class GazetteerRecognizer:

  def __init__(self):
    self.matcher = NameMatcher()
    self.defaults = Gazetteer.defaults()
    self.lookup_tree = {}
    for toponym in self.defaults:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)
    self.demonyms = {}
    for toponym, demonyms in Gazetteer.demonyms().items():
      if toponym not in self.defaults:
        continue
      for demonym in demonyms:
        self.demonyms[demonym] = self.defaults[toponym]

  def find_top_level_toponyms(self, doc):
    matches = {}

    def commit_top(c):
      matches[c.match] = self.defaults[c.lookup_phrase]
      return True

    self.matcher.find_matches(doc, self.lookup_top, commit_top)
    return matches

  def find_demonyms(self, doc):
    matches = {}

    def commit_demonym(c):
      matches[c.match] = self.demonyms[c.lookup_phrase]
      return True

    self.matcher.find_matches(doc, self.lookup_demonym, commit_demonym)
    return matches

  def lookup_top(self, prefix):
    key = prefix[:2]
    if key not in self.lookup_tree:
      return []
    toponyms = self.lookup_tree[key]
    return [t for t in toponyms if t.startswith(prefix)]

  def lookup_demonym(self, prefix):
    return [d for d in self.demonyms if d.startswith(prefix)]
