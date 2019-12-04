import spacy
from .model import ToponymMap


class ToponymRecognizer:

  def __init__(self, nlp_model):
    model = 'en_core_web_sm'
    if nlp_model == 1: model = 'en_core_web_md'
    elif nlp_model == 2: model = 'en_core_web_lg'
    self.nlp = spacy.load(model, disable=['parser'])

  def parse(self, text):
    doc = self.nlp(text)
    tmap = self.get_toponyms(doc)
    anchors = self.get_anchors(doc)
    return (tmap, anchors)

  def get_toponyms(self, doc):
    tmap = ToponymMap()
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
      tmap.add(name, pos)
    return tmap

  def get_anchors(self, doc):
    anchors = []
    for token in doc:
      if token.pos_ == 'PROPN' and token.text[0].isupper():
        anchors.append((token.idx, token.idx + len(token)))
    return anchors
