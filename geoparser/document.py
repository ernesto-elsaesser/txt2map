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

  def __init__(self, text):
    self.text = text + ' ' # allow matching of last word
    self._anns = []

  def import_json(self, json_str):
    data = json.loads(json_str)
    for layer, arrarr in data.items():
      for arr in arrarr:
        a = Annotation(layer, arr[0], arr[1], arr[2], arr[3])
        self._anns.append(a)

  def export_json(self):
    data = {}
    for a in self._anns:
      if a.layer not in data:
        data[a.layer] = []
      data[a.layer].append([a.pos, a.phrase, a.group, a.data])
    return json.dumps(data)

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

  def clear(self, layer):
    self._anns = [a for a in self._anns if a.layer != layer]

  def clear_overlaps(self, layer):
    anns = self.get(layer)
    anns_by_start = {}
    for a in anns:
      if a.pos in anns_by_start:
        other = anns_by_start[a.pos]
        if a.end_pos() <= other.end_pos():
          continue
      anns_by_start[a.pos] = a
    
    starts = sorted(anns_by_start.keys())
    for i in range(len(anns_by_start)-1):
      last_end = anns_by_start[starts[i]].end_pos()
      next_start = starts[i+1]
      if last_end >= next_start:
        overlapped = anns_by_start[next_start]
        self._anns.remove(overlapped)

  def annotated_positions(self, layer):
    return [a.pos for a in self.get(layer)]
