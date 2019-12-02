import spacy
from .model import Toponym


class ToponymRecognizer:

  def __init__(self):
    self.nlp = spacy.load('en_core_web_md', disable=['parser'])

  def parse(self, text):
    doc = self.nlp(text)
    toponyms = self.get_toponyms(doc)
    anchors = self.get_anchors(doc)
    return (toponyms, anchors)

  def get_toponyms(self, doc):
    toponyms = {}
    for ent in doc.ents:
      if ent.label_ not in ['GPE', 'LOC']:
        continue
      name = ent.text
      pos = ent.start_char
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
        pos += 4
      if name not in toponyms:
        toponyms[name] = Toponym(name, [pos])
      else:
        toponyms[name].positions.append(pos)
    return toponyms.values()

  def get_anchors(self, doc):
    anchors = []
    for token in doc:
      if token.pos_ == 'PROPN' and token.text[0].isupper():
        anchors.append((token.idx, token.idx + len(token)))
    return anchors
