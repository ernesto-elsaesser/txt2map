import os
import json
import csv
import re
import spacy
from .document import Document
from .matcher import NameMatcher
from .gazetteer import Gazetteer

class ToponymRecognizer:

  def __init__(self, gns_cache, use_large_model):
    self.use_large_model = use_large_model
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    if self.use_large_model:
      self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])
    self.gaz = Gazetteer(gns_cache)
    self.matcher = NameMatcher(['num','stp'], 2, False)

  def parse(self, text):
    doc = Document(text)

    spacy_doc = self.nlp_sm(text)
    self._add_name_tokens(spacy_doc, doc)

    self.matcher.recognize_names(doc, 'gaz', self.gaz.lookup_prefix)

    ents = spacy_doc.ents
    if self.use_large_model:
      ents += self.nlp_lg(text).ents

    self._add_ner_toponyms(ents, doc)
    return doc

  def _add_name_tokens(self, tokens, doc):
    for token in tokens:
      first = token.text[0]
      is_num = first.isdigit()
      is_title = first.isupper()
      if is_title or is_num:
        group = 'tit'
        if is_num:
          group = 'num'
        elif token.is_stop and not token.text == 'US':
          group = 'stp'  # "US" is considered a stopword ...
        doc.annotate('tok', token.idx, token.text, group, '')

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
