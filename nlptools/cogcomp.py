import requests

class CogCompClient:

  @staticmethod
  def annotate(doc):
    text = doc.text()

    esc_text = text.replace('[', '{').replace(']', '}')
    body = esc_text.encode('utf-8')
    response = requests.post(url='http://localhost:8002', data=body)
    response.encoding = 'utf-8'
    cc_text = response.text

    l = len(text)
    cc_l = len(cc_text)
    i = pos = 0
    ent_pos = ent_group = ent_phrase = None

    while pos < l and i < cc_l:
      c = cc_text[i]
      oc = text[pos]
      if c == '[':
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
      elif (c == '{' and oc == '[') or (c == '}' and oc == ']'):
        assert ent_phrase == None
        i += 1
        pos += 1
      elif c == oc:
        if ent_phrase != None:
          ent_phrase += oc
        pos += 1
        i += 1
      else:
        assert False
