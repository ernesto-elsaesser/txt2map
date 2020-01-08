import re
import spacy
from geoparser import Document

class SpacyNLP:

  def __init__(self):
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

  def annotate(self, doc):
    text = doc.text()

    spacy_doc_sm = self.nlp_sm(text)
    spacy_doc_lg = self.nlp_lg(text)
    unique_names = []

    # named entities
    for ent in spacy_doc_lg.ents:
      name = self._normalized_name(ent)
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, 'spacy_lg', ent.label_)

    for ent in spacy_doc_sm.ents:
      name = self._normalized_name(ent)
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, 'spacy_sm', ent.label_)

    # matching anchors
    for token in spacy_doc_lg:
      first = token.text[0]
      if first.isdigit():
        group = 'num'
      elif first.isupper():
        group = 'stp' if token.is_stop else 'til'
      else:
        continue
      doc.annotate('mat', token.idx, token.text, group, '')

    return doc

  def _normalized_name(self, entity):
    name = entity.text
    if name.startswith('the ') or name.startswith('The '):
      name = name[4:]
    if name.endswith('\n'):
      name = name[:-1]
    if name.endswith('\'s'):
      name = name[:-2]
    elif name.endswith('\''):
      name = name[:-1]
    return name

  def _annotate_all_occurences(self, doc, name, group, data):
    escaped_name = re.escape(name)
    matches = re.finditer(escaped_name, doc.text())
    for match in matches:
      doc.annotate('ner', match.start(), name, group, data)
