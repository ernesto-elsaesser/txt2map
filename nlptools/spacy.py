import re
import requests
import spacy

class SpacyNLP:

  label_map_lg = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'fac', 'ORG': 'org', 
                  'PERSON': 'per', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}
  label_map_sm = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'msc', 'ORG': 'msc',
                  'PERSON': 'msc', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}

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
      if ent.label_ not in self.label_map_lg:
        continue
      name = self._normalized_name(ent)
      group = self.label_map_lg[ent.label_]
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, group, 'spacy_lg')

    for ent in spacy_doc_sm.ents:
      if ent.label_ not in self.label_map_sm:
        continue
      name = self._normalized_name(ent)
      group = self.label_map_sm[ent.label_]
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, group, 'spacy_sm')


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
    phrase = name.rstrip('.')
    for match in matches:
      pos = match.start()
      doc.annotate('ner', pos, phrase, group, data)
      if group == 'loc':
        doc.annotate('rec', pos, phrase, 'ner', phrase)


class SpacyClient:

  @staticmethod
  def annotate(doc):
    body = doc.text().encode('utf-8')
    response = requests.post(url='http://localhost:8001', data=body)
    response.encoding = 'utf-8'
    doc.set_annotation_json(response.text)
