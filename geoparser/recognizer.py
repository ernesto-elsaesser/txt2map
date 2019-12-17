import os
import json
import csv
import re
import spacy
from .model import Document
from .matcher import NameMatcher

class ToponymRecognizer:

  def __init__(self, use_large_model):
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

    self.matcher = NameMatcher()

  def parse(self, text):
    doc = Document(text)

    spacy_doc = self.nlp_sm(text)
    self._add_anchors(spacy_doc, doc)

    names = self.matcher.find_names(doc, False, self._lookup_prefix)
    for name, positions in names.items():
      toponym = name
      if toponym in self.demonyms:
        toponym = self.demonyms[toponym]
      geoname = self.defaults[toponym]
      doc.resolve_globally(name, positions, geoname)

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
      if first.isdigit():
        doc.add_num_anchor(token.idx, token.text)
      elif first.isupper() and not token.is_stop:
        doc.add_anchor(token.idx, token.text)

  def _add_ner_toponyms(self, ents, doc):

    known_toponyms = doc.global_toponyms()
    new_toponyms = {}

    for ent in ents:
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
      doc.recognize_globally(toponym, positions)
