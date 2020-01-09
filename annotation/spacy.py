import re
import requests
import spacy

class SpacyNLP:

  label_map_lg = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'fac', 'ORG': 'org', 
                  'PERSON': 'per', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}
  label_map_sm = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'msc', 'ORG': 'msc',
                  'PERSON': 'msc', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}

  def __init__(self, large_model):
    model = 'en_core_web_lg' if large_model else 'en_core_web_sm'
    self.nlp = spacy.load(model, disable=['parser'])
    self.label_map = self.label_map_lg if large_model else self.label_map_sm
    self.ann_data = 'spacy_lg' if large_model else 'spacy_sm'

  def annotate_ntk(self, doc):
    spacy_doc = self.nlp(doc.text)
    for token in spacy_doc:
      first = token.text[0]
      if first.isdigit():
        group = 'num'
      elif first.isupper():
        group = 'stp' if token.is_stop else 'til'
      else:
        continue
      doc.annotate('ntk', token.idx, token.text, group, '')

  def annotate_ner(self, doc):
    spacy_doc = self.nlp(doc.text)
    unique_names = []
    for ent in spacy_doc.ents:
      if ent.label_ not in self.label_map:
        continue
      name = self._normalized_name(ent)
      group = self.label_map[ent.label_]
      if name not in unique_names:
        unique_names.append(name)
        self._annotate_all_occurences(doc, name, group)


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

  def _annotate_all_occurences(self, doc, name, group):
    escaped_name = re.escape(name)
    matches = re.finditer(escaped_name, doc.text)
    phrase = name.rstrip('.')
    for match in matches:
      doc.annotate('ner', match.start(), phrase, group, self.ann_data)


class SpacyClient:

  def __init__(self, port):
    self.url = f'http://localhost:{port}'

  def annotate_ntk_ner(self, doc):
    body = doc.text.encode('utf-8')
    response = requests.post(url=self.url, data=body)
    response.encoding = 'utf-8'
    doc.import_layers(response.text)
