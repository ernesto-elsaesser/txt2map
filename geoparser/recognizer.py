import os
import json
import csv
import re
import spacy
from .document import Document
from .matcher import NameMatcher
from .gazetteer import Gazetteer
from .config import Config

class ToponymRecognizer:

  def __init__(self, gazetteer):
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    if Config.recog_large_ner_model:
      self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])
    self.gaz = gazetteer
    self.matcher = NameMatcher(['num','stp'], 2) # 2 for US, UK, ...

  def parse(self, text):
    doc = Document(text)

    spacy_doc = self.nlp_sm(text)
    ents = spacy_doc.ents
    person_ents = ents
    if Config.recog_large_ner_model:
      lg_ents = self.nlp_lg(text).ents
      ents += lg_ents
      person_ents = lg_ents # lg is far better in recognizing persons

    person_pos = []
    for ent in person_ents:
      if ent.label_ == 'PERSON':
        for token in ent:
          person_pos.append(token.idx)

    self._add_ner_toponyms(ents, doc)
    self._add_name_tokens(spacy_doc, doc, person_pos)
    self.matcher.recognize_names(doc, 'gaz', self.gaz.lookup_prefix)

    doc.clear_overlaps('rec')
    return doc

  def _add_name_tokens(self, tokens, doc, person_pos):
    for token in tokens:
      if token.idx in person_pos:
        continue
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
    seen = []
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

      if name in seen:
        continue
      seen.append(name)

      for match in re.finditer(re.escape(name), doc.text):
        doc.annotate('rec', match.start(), name, 'ner', name)
