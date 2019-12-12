import os
import json
import csv
import re
import spacy
from .model import ToponymMap

class ToponymRecognizer:

  def __init__(self, use_large_model):
    self.use_large_model = use_large_model
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    if use_large_model:
      self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

    dirname = os.path.dirname(__file__)
    top_level_file = dirname + '/top-level.json'
    with open(top_level_file, 'r') as f:
      json_dict = f.read()
    names = json.loads(json_dict)
    self.top_level_names = list(names.keys())

    self.demonyms = []
    demonyms_file = dirname + '/demonyms.csv'
    with open(demonyms_file, 'r') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        self.demonyms += row[1].split(',')

  def parse(self, text):
    doc = self.nlp_sm(text)
    ents = doc.ents
    if self.use_large_model:
      ents += self.nlp_lg(text).ents
    tmap = self._get_toponyms(text, ents)
    anchors = self._get_anchors(doc)
    return (tmap, anchors)

  def _get_toponyms(self, text, ents):
    tmap = ToponymMap()

    for name in self.top_level_names:
      for match in re.finditer(name, text):
        tmap.add(name, match.start())
    for demonym in self.demonyms:
      for match in re.finditer(demonym, text):
        tmap.add(demonym, match.start())

    for ent in ents:
      if ent.label_ not in ['GPE', 'LOC', 'NORP']:
        continue

      pos = ent.start_char
      name = ent.text
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
        pos += 4
      if name.endswith('\'s'):
        name = name[:-2]
      elif name.endswith('\''):
        name = name[:-1]

      tmap.add(name, pos)

    return tmap

  def _get_anchors(self, doc):
    anchors = []
    for token in doc:
      first = token.text[0]
      if first.isdigit() or (token.pos_ == 'PROPN' and first.isupper()):
        anchors.append((token.idx, token.text))
    return anchors
