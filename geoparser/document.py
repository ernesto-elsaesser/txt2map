import json

class Layer:

  ner = 'ner' # recognized entities
  topo = 'topo' # recognized locations
  gres = 'gres' # global resolution
  lres = 'lres' # local resolution
  wiki = 'wiki' # Wikipedia URLs
  gold = 'gold' # gold annotations


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

  def annotate(self, layer, pos, phrase, group, data='', replace_shorter=False, replace_identical=False):
    if layer not in self.anns:
      self.anns[layer] = []

    l = len(phrase)
    end = pos + len(phrase)
    ann = [pos, phrase, group, data]

    anns_by_index = self.annotations_by_index(layer)
    deleted = []
    for i in range(pos, end):
      if i in anns_by_index:
        overlap = anns_by_index[i]
        ol = len(overlap.phrase) 
        if (replace_shorter and ol < l) or (replace_identical and ol == l):
          if overlap.pos in deleted:
            continue
          print(f'{layer} - annotation {phrase} [{group}] replaces {overlap.phrase} [{overlap.group}]')
          self.delete_annotation(layer, overlap.pos)
          deleted.append(overlap.pos)
        else:
          print(f'{layer} - annotation {phrase} [{group}] blocked by {overlap.phrase} [{overlap.group}]')
          return False

    self.anns[layer].append(ann)
    return True

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

  def get(self, layer, pos):
    if layer not in self.anns:
      return False
    for arr in self.anns[layer]:
      if arr[0] == pos:
        return Annotation(layer, arr[0], arr[1], arr[2], arr[3])
    return None

  def get_all(self, layer, group=None, pos_range=None):
    if layer not in self.anns:
      return []

    annotations = []
    for arr in self.anns[layer]:
      if group != None and arr[2] != group:
        continue
      if pos_range != None and arr[0] not in pos_range:
        continue
      a = Annotation(layer, arr[0], arr[1], arr[2], arr[3])
      annotations.append(a)

    return annotations
    
  def annotations_by_index(self, layer, group=None):
    anns_by_index = {}
    for a in self.get_all(layer, group):
      for i in range(a.pos, a.end_pos()):
        anns_by_index[i] = a
    return anns_by_index

  def annotations_by_position(self, layer, group=None):
    return {a.pos: a for a in self.get_all(layer, group)}
