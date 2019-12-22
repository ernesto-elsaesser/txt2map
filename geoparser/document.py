import json


class Annotation:

  def __init__(self, layer, pos, phrase, group, data):
    self.layer = layer
    self.pos = pos
    self.phrase = phrase
    self.group = group
    self.data = data

  def __repr__(self):
    return f'{self.layer}: {self.phrase} [{self.pos}/{self.group}]'


class Document:

  def __init__(self, text):
    self.text = text + ' ' # allow matching of last word
    self._anns = []

  def load_annotations(self, file_path):
    with open(file_path, 'r') as f:
      data = json.load(f)
    for layer in data:
      for arr in layer:
        a = Annotation(layer, arr[0], arr[1], arr[2], arr[3])
        self._anns.append(a)

  def save_annotations(self, file_path):
    data = {}
    for a in self._anns:
      if a.layer not in data:
        data[a.layer] = []
      data[a.layer].append([a.pos, a.phrase, a.group, a.data])
    with open(file_path, 'w') as f:
      json.dump(data, f)

  def annotate(self, layer, pos, phrase, group, data):
    a = Annotation(layer, pos, phrase, group, data)
    self._anns.append(a)
    return a

  def get(self, layer, group=None, exclude_groups=[], pos=None):
    annotations = []
    for a in self._anns:
      if a.layer != layer:
        continue
      if group != None and a.group != group:
        continue 
      if a.group in exclude_groups:
        continue
      if pos != None and a.pos != pos:
        continue
      annotations.append(a)
    return annotations

  def annotated_positions(self, layer):
    return [a.pos for a in self.get(layer)]
