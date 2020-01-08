import json


class Annotation:

  def __init__(self, layer, pos, phrase, group, data):
    self.layer = layer
    self.pos = pos
    self.phrase = phrase
    self.group = group
    self.data = data

  def end_pos(self):
    return self.pos + len(self.phrase)

  def __repr__(self):
    return f'{self.layer}: {self.phrase} [{self.pos}/{self.group}]'


class Document:

  def __init__(self, text=''):
    self.data = {'text': text, 'anns': {}}
      
  def get_json(self):
    return json.dumps(self.data)
      
  def set_json(self, json_str):
    self.data = json.loads(json_str)

  def text(self):
    return self.data['text']

  def annotate(self, layer, pos, phrase, group, data):
    if layer not in self.data['anns']:
      self.data['anns'][layer] = []

    end = pos + len(phrase)
    anns_by_index = self.annotations_by_index(layer)
    if pos in anns_by_index:
      prev = anns_by_index[pos]
      if prev.pos < pos:
        print(f'Not added because of partial overlap: {layer}: {phrase} [{pos}/{group}]')
        return
      if prev.pos == pos and prev.end_pos() >= end:
        return
      self.delete_annotation(layer, prev.pos)
      print(f'Extended because of full overlap: {a} -> {phrase} [{group}]')

    anns_by_pos = self.annotations_by_position(layer)
    for i in range(pos, end):
      if i in anns_by_pos:
        self.delete_annotation(layer, i)
        print(f'Deleted because of partial overlap: {anns_by_pos[i]} -> {phrase} [{group}]')

    ann = [pos, phrase, group, data]
    self.data['anns'][layer].append(ann)

  def update_annotation_data(self, layer, pos, new_data):
    anns = self.data['anns'][layer]
    for i in range(len(anns)):
      if anns[i][0] == pos:
        self.data['anns'][layer][i][3] = new_data

  def delete_layer(self, layer):
    del self.data['anns'][layer]

  def delete_annotation(self, layer, pos):
    anns = self.data['anns'][layer]
    filtered = [a for a in anns if a[0] != pos]
    self.data['anns'][layer] = filtered

  def get(self, layer, group=None, exclude_groups=[], pos=None):
    if layer not in self.data['anns']:
      return []

    annotations = []
    for arr in self.data['anns'][layer]:
      if group != None and arr[2] != group:
        continue 
      if arr[2] in exclude_groups:
        continue
      if pos != None and arr[0] != pos:
        continue
      a = Annotation(layer, arr[0], arr[1], arr[2], arr[3])
      annotations.append(a)
    
    return annotations

  def annotations_by_index(self, layer, group=None):
    anns_by_index = {}
    for a in self.get(layer, group=group):
      for i in range(a.pos, a.end_pos()):
        anns_by_index[i] = a
    return anns_by_index

  def annotations_by_position(self, layer):
    return {a.pos: a for a in self.get(layer)}
