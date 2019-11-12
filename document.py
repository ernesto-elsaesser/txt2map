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
