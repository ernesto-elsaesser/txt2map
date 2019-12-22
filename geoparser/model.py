
class GeoName:

  # data: dict
  # row: tupel
  def __init__(self, data=None, row=None):
    if data != None:
      self.id = data['geonameId']
      self.name = data['name']
      self.population = data['population']
      self.lat = float(data['lat'])
      self.lon = float(data['lng'])
      self.cc = '-' if 'countryCode' not in data else data['countryCode']
      self.adm1 = '-' if 'adminCode1' not in data else data['adminCode1']
      self.fcl = '-' if 'fcl' not in data else data['fcl']
      self.fcode = '-' if 'fcode' not in data else data['fcode']
      # not cached:
      if 'asciiName' in data:
        self.asciiname = data['asciiName']
      if 'alternateNames' in data:
        self.altnames = data['alternateNames']
    else:
      self.id = row[0]
      self.name = row[1]
      self.population = row[2]
      self.lat = row[3]
      self.lon = row[4]
      self.fcl = row[5]
      self.fcode = row[6]
      self.cc = row[7]
      self.adm1 = row[8]
    
    self.is_city = self.fcl == 'P'
    self.is_country = self.fcode.startswith('PCL')
    self.is_continent = self.fcode == 'CONT'
    self.is_ocean = self.fcode == 'OCN'
  
  def region(self):
    return f'{self.cc}-{self.adm1}'

  def __repr__(self):
    return f'{self.name}, {self.adm1}, {self.cc} [{self.fcode}]'


class Document:

  def __init__(self, text, annotations=None):
    self.text = text + ' ' # allow matching of last word
    self.annotations = annotations or {}

  def annotate(self, layer, pos, phrase, group='', data=''):
    if layer not in self.annotations:
      self.annotations[layer] = []
    ann = {'pos': pos, 'phrase': phrase, 'group': group, 'data': data}
    self.annotations[layer].append(ann)

  def clear_group(self, layer, group):
    anns = self.annotations[layer]
    cleared_anns = [a for a in anns if a['group'] != group]
    self.annotations[layer] = cleared_anns

  def iter(self, layer, select=None, exclude=[]):
    if layer not in self.annotations:
      return
    copy = list(self.annotations[layer])
    for a in copy:
      group = a['group']
      if select != None and group != select:
        continue 
      if group in exclude:
        continue
      yield (a['pos'], a['phrase'], group, a['data'])

  def annotated_positions(self, layer):
    return [p for p,_,g,_ in self.iter(layer)]

  def iter_pos(self, pos, layer):
    if layer not in self.annotations:
      return
    for a in self.annotations[layer]:
      if a['pos'] == pos:
        yield (a['phrase'], a['group'], a['data'])


class TreeNode:

  def __init__(self, key, parent):
    self.key = key
    self.parent = parent
    self.children = {}  # key: TreeNode
    self.geonames = {}  # phrase: GeoName
    self.positions = {}  # phrase: [pos]

  def __repr__(self):
    return self.key

  def get(self, key_path, create):
    if len(key_path) == 0:
      return self
    key = key_path[0]
    if key not in self.children:
      if create:
        child = TreeNode(key, self)
        self.children[key] = child
      else:
        return None
    else:
      child = self.children[key]
    return child.get(key_path[1:], create)

  def add(self, phrase, geoname, position):
    if phrase not in self.geonames:
      self.geonames[phrase] = geoname
      self.positions[phrase] = [position]
    else:
      self.positions[phrase].append(position)

  def iter(self):
    node = self
    while node.key != None:
      yield node
      node = node.parent

  def mentions(self):
    return sum(len(ps) for ps in self.positions.values())

  def branch_mentions(self):
    return [n.mentions() for n in self.iter()]


