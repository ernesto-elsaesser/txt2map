import re
from .matcher import NameMatcher
from .gazetteer import Gazetteer
from .geonames import GeoNamesCache

class GazetteerRecognizer:

  def __init__(self):
    self.matcher = NameMatcher()

    self.cities = Gazetteer.cities()
    self.lookup_tree = {}
    for city in self.cities:
      key = city[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(city)

  def annotate_rec(self, doc):
    for a in doc.get_all('ner', 'loc'):
      doc.annotate('rec', a.pos, a.phrase, 'glo', a.phrase)

    persons = set()
    for a in doc.get_all('ner', 'per'):
      persons.add(a.phrase)

    orgs = set()
    for a in doc.get_all('ner', 'org'):
      orgs.add(a.phrase)

    rec_indices = doc.annotations_by_index('rec')

    def commit_toponym(c):
      if c.pos in rec_indices:
        return
      for p in persons:
        if c.match in p and len(p) > len(c.match):
          return False
      for o in orgs:
        if c.match in o and len(o) > len(c.match):
          return False
      if doc.text[c.end] in [' ', '-'] and doc.text[c.end+1].isupper():
        return False
      doc.annotate('rec', c.pos, c.match, 'glo', c.lookup_phrase, replace_shorter=True)
      print('ADDED GAZ TOPO: ' + c.match)
      return True

    self.matcher.find_matches(doc, self._lookup_toponym, commit_toponym)

  def _lookup_toponym(self, prefix):
    key = prefix[:2]
    if key not in self.lookup_tree:
      return []
    toponyms = self.lookup_tree[key]
    return [t for t in toponyms if t.startswith(prefix)]
