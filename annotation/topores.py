import requests
import csv
from .exception import PipelineException


class TopoResolverClient:

  def __init__(self, url=None):
    self.server_url = url

  def annotate_res(self, doc):
    if self.server_url == None:
      raise PipelineException('TopoResolver service not configured!')

    req_data = doc.text.encode('utf-8')
    try:
      response = requests.post(url=self.server_url, data=req_data, timeout=10)
    except:
      raise PipelineException('TopoResolver service not running!')
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

