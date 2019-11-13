from nltk.tokenize import word_tokenize
from nltk.tokenize.util import align_tokens

class Document:

  def __init__(self, text):
    self.text = text
    self.l = len(text)
    self.anchors = []

    tokens = word_tokenize(text)
    for start, end in align_tokens(tokens, text):
      if not Document.is_anchor(text, start):
        continue
      if (end - start) == 1: # for 1-char tokens include the 2 following chars
        end = start + 3
        if end >= self.l:
          continue
      self.anchors.append((text[start:end], start, end))

  @staticmethod
  def is_anchor(text, index):
    c = ord(text[index])
    if 65 <= c <= 90:  # A-Z
      return True
    elif 48 <= c <= 57:  # 0-9
      return True
    else:
      return False


class Match:

  def __init__(self, name, positions, refs, context):
    self.name = name
    self.positions = positions
    self.refs = refs
    self.context = context

  def to_json(self):
    nodes = self.inflate_ref_urls('node', self.refs[0])
    ways = self.inflate_ref_urls('way', self.refs[1])
    relations = self.inflate_ref_urls('relation', self.refs[2])
    return {'name': self.name,
            'positions': self.positions,
            'elements': nodes + ways + relations,
            'context': self.context}

  def inflate_ref_urls(self, type_name, refs):
    # NOTE: base URL can probably be dropped
    return list(map(lambda r: f'https://www.openstreetmap.org/{type_name}/{r}', refs))
