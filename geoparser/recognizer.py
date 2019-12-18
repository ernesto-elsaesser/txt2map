import os
import json
import csv
import re
import spacy
from .model import Document
from .matcher import NameMatcher

class ToponymRecognizer:

  def __init__(self, gns_cache, use_large_model):
    self.gns_cache = gns_cache

    # TODO: check if large model makes difference
    self.use_large_model = False #use_large_model
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    if self.use_large_model:
      self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

    dirname = os.path.dirname(__file__)
    defaults_file = dirname + '/defaults.json'
    with open(defaults_file, 'r') as f:
      json_dict = f.read()
    self.defaults = json.loads(json_dict)

    self.demonyms = {}
    demonyms_file = dirname + '/demonyms.csv'
    with open(demonyms_file, 'r') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        toponym = row[0]
        demos = row[1].split(',')
        for demonym in demos:
          self.demonyms[demonym] = toponym

    self.lookup_tree = {}
    known_toponyms = list(self.defaults.keys()) + list(self.demonyms.keys())
    for toponym in known_toponyms:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

    self.matcher = NameMatcher(False, False, 2, False)

  def parse(self, text):
    doc = Document(text)

    spacy_doc = self.nlp_sm(text)
    self._add_anchors(spacy_doc, doc)

    results = self.matcher.find_names(doc, self._lookup_prefix)
    for match, completions in results.items():
      positions = [c.start for c in completions]
      doc.recognize(match, positions)
      toponym = completions[0].db_name
      if toponym in self.demonyms:
        toponym = self.demonyms[toponym]
      geoname_id = self.defaults[toponym]
      geoname = self.gns_cache.get(geoname_id)
      doc.resolve(match, geoname)

    ents = spacy_doc.ents
    if self.use_large_model:
      ents += self.nlp_lg(text).ents

    self._add_ner_toponyms(ents, doc)
    return doc

  def _lookup_prefix(self, prefix):
    key = prefix[:2]
    if key not in self.lookup_tree:
      return []
    toponyms = self.lookup_tree[key]
    return [t for t in toponyms if t.startswith(prefix)]

  def _add_anchors(self, tokens, doc):
    for token in tokens:
      first = token.text[0]
      is_num = first.isdigit()
      is_title = first.isupper()
      if is_title or is_num:
        is_stop = token.is_stop and not token.text == 'US'
        doc.add_anchor(token.idx, token.text, is_num, is_stop)

  def _add_ner_toponyms(self, ents, doc):

    known_toponyms = doc.toponyms()
    new_toponyms = {}

    for ent in ents:
      if ent.label_ == 'PERSON':
        names = ent.text.split(' ')
        for name in names:
          doc.clear(name)

      if ent.label_ not in ['GPE', 'LOC']:
        continue

      start = ent.start_char
      name = ent.text
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
        start += 4
      if name.endswith('\'s'):
        name = name[:-2]
      elif name.endswith('\''):
        name = name[:-1]

      is_known = False
      for known in known_toponyms:
        if name in known:
          is_known = True
          break

      if is_known:
        continue

      if name not in new_toponyms:
        new_toponyms[name] = []
      new_toponyms[name].append(start)

    for toponym, positions in new_toponyms.items():
      doc.recognize(toponym, positions)
