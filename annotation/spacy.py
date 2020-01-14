import re
import requests
from .exception import PipelineException


class SpacyClient:

  label_map = {'GPE': 'loc', 'LOC': 'loc', 'NORP': 'loc', 'FAC': 'fac', 'ORG': 'org', 'PERSON': 'per', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LANGUAGE': 'msc'}

  def __init__(self, url=None):
    self.server_url = url

  def annotate_ner(self, doc):
    if self.server_url == None:
      raise PipelineException('spaCy NER service not configured!')

    req_data = doc.text.encode('utf-8')
    try:
      response = requests.post(url=self.server_url, data=req_data, timeout=15)
    except:
      raise PipelineException('spaCy NER service not running!')
    response.encoding = 'utf-8'

    ent_map = response.json()
    lg_ents = ent_map['lg']
    for name, label in lg_ents.items():
      if label not in self.label_map:
        continue
      group = self.label_map[label]
      phrase = self._normalized_name(name)
      escaped_phrase = re.escape(phrase)
      matches = re.finditer(escaped_phrase, doc.text)
      phrase = phrase.rstrip('.') # for consistency with CogComp
      for match in matches:
        doc.annotate('ner', match.start(), phrase, group, 'spacy_lg')

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
