import re
import requests
import spacy
from .exception import PipelineException


class SpacyClient:

  label_map_lg = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'fac', 'ORG': 'org',
                  'PERSON': 'per', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}
  label_map_sm = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'msc', 'ORG': 'msc',
                  'PERSON': 'msc', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}

  def __init__(self, url=None):
    self.server_url = url
    self.nlp = spacy.load('en_core_web_sm', disable=['parser'])

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
    if self.server_url == None:
      raise PipelineException('spaCy NER service not configured!')

    req_data = doc.text.encode('utf-8')
    try:
      response = requests.post(url=self.server_url, data=req_data)
    except:
      raise PipelineException('spaCy NER service not running!')
    response.encoding = 'utf-8'

    unique_names = []

    lg_ents = response.json()
    for name, label in lg_ents.items():
      if label not in self.label_map_lg:
        continue
      phrase = self._normalized_name(name)
      if phrase not in unique_names:
        unique_names.append(name)
        group = self.label_map_lg[label]
        self._annotate_all_occurences(doc, phrase, group, 'spacy_lg')

    spacy_doc = self.nlp(doc.text)
    for ent in spacy_doc.ents:
      if ent.label_ not in self.label_map_sm:
        continue
      phrase = self._normalized_name(ent.text)
      if name not in unique_names:
        unique_names.append(name)
        group = self.label_map_sm[ent.label_]
        self._annotate_all_occurences(doc, name, group, 'spacy_sm')

  def _normalized_name(self, name):
    if name.startswith('the ') or name.startswith('The '):
      name = name[4:]
    if name.endswith('\n'):
      name = name[:-1]
    if name.endswith('\'s'):
      name = name[:-2]
    elif name.endswith('\''):
      name = name[:-1]
    return name

  def _annotate_all_occurences(self, doc, phrase, group, data):
    escaped_phrase = re.escape(phrase)
    matches = re.finditer(escaped_phrase, doc.text)
    phrase = phrase.rstrip('.') # for consistency with CogComp
    for match in matches:
      doc.annotate('ner', match.start(), phrase, group, data)
