import requests
import csv
from geoparser import Pipeline, Step

class TopoResolverClient(Step):

  def __init__(self):
    self.server_url = url

  def create_pipeline(self):
    pipe = Pipeline()
    pipe.add(self)
    return pipe

  def annotate(self, doc):
    self.annotate_res(doc)

  def annotate_res(self, doc):
    req_data = doc.text.encode('utf-8')
    response = requests.post(url=self.server_url, data=req_data, timeout=10)
    response.encoding = 'utf-8'
    rows = response.text.split('\n')
    for row in rows:
      if len(row) == 0:
        continue
      columns = row.split('\t')
      pos = int(columns[1])
      phrase = columns[0]
      geoname_id = int(columns[2])
      doc.annotate('rec', pos, phrase, 'glo', '')
      doc.annotate('res', pos, phrase, 'glo', geoname_id)

