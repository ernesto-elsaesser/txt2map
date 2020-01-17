import requests
from .exception import PipelineException

class CogCompClient:

  def __init__(self, url):
    self.server_url = url

  def annotate_ner(self, doc):
    if self.server_url == None:
      raise PipelineException('CogComp NER service not configured!')

    text = doc.text

    esc_text = text.replace('[', '{').replace(']', '}')
    req_data = esc_text.encode('utf-8')
    try:
      response = requests.post(url=self.server_url, data=req_data, timeout=15)
    except:
      raise PipelineException('CogComp NER service not running!')
    response.encoding = 'utf-8'
    cc_text = response.text

    l = len(text)
    cc_l = len(cc_text)
    i = pos = 0
    ent_pos = ent_group = ent_phrase = None

    ticks = ['"','\'','`']

    while pos < l and i < cc_l:
      c = cc_text[i]
      oc = text[pos]

      if c in ticks:
        i += 1
      elif oc in ticks:
        pos += 1
      elif c == '[':
        ent_pos = pos
        ent_phrase = ''
        if cc_text[i+1] == 'M':
          ent_group = 'msc'
          i += 6
        else:
          ent_group = cc_text[i+1:i+4].lower()
          i += 5
      elif c == ']':
        if ent_phrase.startswith('The ') or ent_phrase.startswith('the '):
          ent_phrase = ent_phrase[4:]
          ent_pos += 4
        doc.annotate('ner', ent_pos, ent_phrase, ent_group, 'ill_ner_conll')
        ent_pos = ent_group = ent_phrase = None
        i += 1
      elif oc == '\n' and c != '\n':
        pos += 1
      elif c == ' ' and oc != ' ':
        i += 1
      elif c == oc or (c == '{' and oc == '[') or (c == '}' and oc == ']'):
        if ent_phrase != None:
          ent_phrase += oc
        pos += 1
        i += 1
      else:
        assert False
