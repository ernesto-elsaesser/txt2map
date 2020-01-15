import requests
import csv
from .exception import PipelineException


class StanfordClient:

  label_map = {'LOCATION': 'loc', 'ORGANIZATION': 'org', 'PERSON': 'per', 'MISC': 'msc'}

  def __init__(self, url=None):
    self.server_url = url

  def annotate_ner(self, doc):
    if self.server_url == None:
      raise PipelineException('Stanford NER service not configured!')

    req_data = doc.text.encode('utf-8')
    try:
      response = requests.post(url=self.server_url, data=req_data, timeout=10)
    except:
      raise PipelineException('Stanford NER service not running!')
    response.encoding = 'utf-8'
    rows = response.text.split('\n')
    for row in rows:
      columns = row.split('\t')
      if len(row) == 0:
        continue
      phrase = columns[0]
      pos = int(columns[1])
      label = columns[2]
      group = self.label_map[label]
      doc.annotate('ner', pos, phrase, group, 'stanford_conll')

