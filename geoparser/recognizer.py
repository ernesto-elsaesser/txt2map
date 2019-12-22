import os
import json
import csv
import re
import spacy
from .model import Document
from .matcher import NameMatcher
from .gazetteer import Gazetteer

class ToponymRecognizer:

  def __init__(self, gns_cache, use_large_model):

    self.use_large_model = use_large_model
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    if self.use_large_model:
      self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

    self.gaz = Gazetteer(gns_cache)

    self.lookup_tree = {}
    for toponym in self.gaz.defaults:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

    self.matcher = NameMatcher(['num','stop'], 2, False)

  def parse(self, text):
    doc = Document(text)

    spacy_doc = self.nlp_sm(text)
    self._add_name_tokens(spacy_doc, doc)

    self.matcher.recognize_names(doc, 'gazetteer', self._lookup_prefix)

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

  def _add_name_tokens(self, tokens, doc):
    for token in tokens:
      first = token.text[0]
      is_num = first.isdigit()
      is_title = first.isupper()
      if is_title or is_num:
        group = ''
        if is_num:
          group = 'num'
        elif token.is_stop and not token.text == 'US':
          group = 'stop'  # "US" is considered a stopword ...
        doc.annotate('names', token.idx, token.text, group)

  def _add_ner_toponyms(self, ents, doc):
    blocked = doc.annotated_positions('rec')

    for ent in ents:
      if ent.label_ not in ['GPE', 'LOC']:
        continue

      name = ent.text
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
      if name.endswith('\'s'):
        name = name[:-2]
      elif name.endswith('\''):
        name = name[:-1]

      for match in re.finditer(re.escape(name), doc.text):
        pos = match.start()
        if pos not in blocked:
          doc.annotate('rec', pos, name, 'ner', name)
