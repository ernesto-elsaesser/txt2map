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
    self.text = text
    self.anns = {}

  def export_layers(self, only_layers=None):
    json_obj = {}
    for layer in self.anns:
      if only_layers == None or layer in only_layers:
        json_obj[layer] = self.anns[layer]
    return json.dumps(json_obj)
      
  def import_layers(self, json_str, only_layers=None):
    json_obj = json.loads(json_str)
    for layer in json_obj:
      if only_layers == None or layer in only_layers:
        self.anns[layer] = json_obj[layer]

  def layers(self):
    return list(self.anns.keys())

  def annotate(self, layer, pos, phrase, group, data):
    if layer not in self.anns:
      self.anns[layer] = []

    end = pos + len(phrase)
    anns_by_index = self.annotations_by_index(layer)
    if pos in anns_by_index:
      prev = anns_by_index[pos]
      if prev.pos < pos:
        return
      if prev.pos == pos and prev.end_pos() >= end:
        return
      self.delete_annotation(layer, prev.pos)
      print(f'Extended annotation {prev} -> {phrase} [{group}]')

    anns_by_pos = self.annotations_by_position(layer)
    for i in range(pos, end):
      if i in anns_by_pos:
        self.delete_annotation(layer, i)
        print(f'Replaced annotation {anns_by_pos[i]} -> {phrase} [{group}]')

    ann = [pos, phrase, group, data]
    self.anns[layer].append(ann)

  def update_annotation(self, layer, pos, new_group, new_data):
    anns = self.anns[layer]
    for i in range(len(anns)):
      if anns[i][0] == pos:
        self.anns[layer][i][2] = new_group
        self.anns[layer][i][3] = new_data

  def delete_layer(self, layer):
    if layer in self.anns:
      del self.anns[layer]

  def delete_annotation(self, layer, pos):
    anns = self.anns[layer]
    filtered = [a for a in anns if a[0] != pos]
    self.anns[layer] = filtered

  def get(self, pos):
    annotations = {}
    for layer, arrs in self.anns.items():
      for arr in arrs:
        if arr[0] == pos:
          a = Annotation(layer, arr[0], arr[1], arr[2], arr[3])
          annotations[layer] = a
          break

    return annotations

  def get_all(self, layer, group=None):
    if layer not in self.anns:
      return []

    annotations = []
    for arr in self.anns[layer]:
      if group == None or arr[2] == group:
        a = Annotation(layer, arr[0], arr[1], arr[2], arr[3])
        annotations.append(a)

    return annotations
    
  def annotations_by_index(self, layer, group=None):
    anns_by_index = {}
    for a in self.get_all(layer, group):
      for i in range(a.pos, a.end_pos()):
        anns_by_index[i] = a
    return anns_by_index

  def annotations_by_position(self, layer):
    return {a.pos: a for a in self.get_all(layer)}
