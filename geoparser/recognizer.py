import os
import json
import re
import spacy
from .model import ToponymMap

class ToponymRecognizer:

  def __init__(self, nlp_model):
    model = 'en_core_web_sm'
    if nlp_model == 1: model = 'en_core_web_md'
    elif nlp_model == 2: model = 'en_core_web_lg'
    self.nlp = spacy.load(model, disable=['parser'])

    dirname = os.path.dirname(__file__)
    top_level_file = dirname + '/top-level.json'
    with open(top_level_file, 'r') as f:
      json_dict = f.read()
    names = json.loads(json_dict)
    self.top_level_names = list(names.keys())

  def parse(self, text):
    doc = self.nlp(text)
    tmap = self._get_toponyms(text, doc)
    anchors = self._get_anchors(doc)
    return (tmap, anchors)

  def _get_toponyms(self, text, doc):
    tmap = ToponymMap()
    for name in self.top_level_names:
      for match in re.finditer(name, text):
        tmap.add(name, match.start())
    for ent in doc.ents:
      if ent.label_ not in ['GPE', 'LOC']:
        continue
      name = ent.text
      pos = ent.start_char
      if name.endswith('\'s'):
        name = name[:-2]
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
        pos += 4
      if not name in self.top_level_names:
        tmap.add(name, pos)
    return tmap

  def _get_anchors(self, doc):
    anchors = []
    for token in doc:
      if token.pos_ == 'PROPN' and token.text[0].isupper():
        anchors.append((token.idx, token.idx + len(token)))
    return anchors
