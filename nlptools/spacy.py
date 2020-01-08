import re
import spacy

class SpacyNLP:

  label_map_lg = {'GPE': 'loc', 'LOC': 'loc', 'FAC': 'fac', 'ORG': 'org', 'PERSON': 'per'}
  label_map_sm = {'GPE': 'loc', 'LOC': 'loc'}

  def __init__(self):
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

  def annotate(self, doc):
    text = doc.text()

    spacy_doc_sm = self.nlp_sm(text)
    spacy_doc_lg = self.nlp_lg(text)
    unique_names = []

    # name takens for gazetteer matching
    for token in spacy_doc_lg:
      first = token.text[0]
      if first.isdigit():
        group = 'num'
      elif first.isupper():
        group = 'stp' if token.is_stop else 'til'
      else:
        continue
      doc.annotate('ntk', token.idx, token.text, group, '')

    # named entities
    for ent in spacy_doc_lg.ents:
      name = self._normalized_name(ent)
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, ent.label_, True)

    for ent in spacy_doc_sm.ents:
      name = self._normalized_name(ent)
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, ent.label_, False)


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

  def _annotate_all_occurences(self, doc, name, label, large_model):
    group = 'msc'
    if large_model:
      data = 'spacy_lg'
      label_map = self.label_map_lg
    else:
      data = 'spacy_sm'
      label_map = self.label_map_sm
    for label in label_map:
      group = label_map[label]
    escaped_name = re.escape(name)
    matches = re.finditer(escaped_name, doc.text())
    for match in matches:
      doc.annotate('ner', match.start(), name, group, data)
