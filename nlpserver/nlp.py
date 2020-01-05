import re
import spacy
from geoparser import Document

class SpacyNLP:

  def __init__(self):
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

  def annotate(self, text):
    doc = Document(text)

    spacy_doc_sm = self.nlp_sm(text)
    sm_ents = spacy_doc_sm.ents
    spacy_doc_lg = self.nlp_lg(text)
    lg_ents = spacy_doc_lg.ents

    person_pos = []
    for ent in lg_ents: # lg is far better at recognizing persons
      if ent.label_ == 'PERSON':
        for token in ent:
          person_pos.append(token.idx)

    self._add_ner_toponyms(sm_ents + lg_ents, doc)
    self._add_name_tokens(spacy_doc_sm, doc, person_pos)

    return doc

  def _add_name_tokens(self, tokens, doc, person_pos):
    for token in tokens:
      first = token.text[0]
      is_num = first.isdigit()
      is_title = first.isupper()
      if is_title or is_num:
        group = 'tic'
        if is_num:
          group = 'num'
        elif token.idx in person_pos:
          group = 'per'
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
      elif name.endswith('\n'):
        name = name[:-1]
      if name.endswith('\'s'):
        name = name[:-2]
      elif name.endswith('\''):
        name = name[:-1]

      if name in seen:
        continue
      seen.append(name)

      for match in re.finditer(re.escape(name), doc.text):
        doc.annotate('rec', match.start(), name, 'ner', name)
