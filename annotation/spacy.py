import requests
import csv
from .exception import PipelineException


class SpacyClient:

  label_map = {'GPE': 'loc', 'LOC': 'loc', 'FAC': 'loc', 'ORG': 'org', 'PERSON': 'per', 
               'NORP': 'dem', 'LANGUAGE': 'lan', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LAW': 'msc'}

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
    rows = response.text.split('\n')
    for row in rows:
      columns = row.split('\t')
      if len(row) == 0:
        continue
      label = columns[2]
      if label not in self.label_map:
        continue
      pos = int(columns[0])
      phrase = self._normalized_name(columns[1])
      group = self.label_map[label]
      doc.annotate('ner', pos, phrase, group, 'spacy_lg')

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
