
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



class ToponymCluster:

  # toponyms: [str]
  # hierarchy: [GeoName]
  # local_context: [GeoName]
  # size: int
  def __init__(self, toponyms, hierarchy, local_context):
    self.toponyms = toponyms
    self.hierarchy = hierarchy
    self.local_context = local_context
    self.anchor = hierarchy[-1]
    self.size = len(toponyms)

  def __repr__(self):
    path_str = ' > '.join(g.name for g in self.hierarchy)
    if self.size == 1:
      return path_str
    names = ', '.join(self.toponyms)
    return f'{path_str} ({names})'


class OSMElement:

  type_names = ['node', 'way', 'relation']

  # id: int
  # element_type: 'node' or 'way' or 'relation'
  def __init__(self, id, element_type):
    self.id = id
    self.element_type = element_type

  def reference(self):
    return self.element_type + '/' + str(self.id)

  def short_ref(self):
    return self.element_type[0] + str(self.id)

  def __repr__(self):
    return self.short_ref()

  def url(self):
    return 'https://www.openstreetmap.org/' + self.reference()

  def type_code(self):
    return self.type_names.index(self.element_type)


class LocalLayer:

  def __init__(self, base, base_hierarchy, global_toponyms, anchor_points, text_mentions):
    self.base = base
    self.base_hierarchy = base_hierarchy
    self.global_toponyms = global_toponyms
    self.anchor_points = anchor_points
    self.text_mentions = text_mentions
    self.confidence = 0

    # recognition: name -> positions
    self.toponyms = {}

    # resolution: name -> osm elements
    self.osm_elements = {}


class Document:

  def __init__(self, text):
    self.text = text + ' ' # allow matching of last word
    self.name_tokens = []
    self.hierarchies = {}
    self.local_layers = []

    # recognition: name -> positions
    self.demonyms = {}
    self.gaz_toponyms = {}
    self.ner_toponyms = {}
    self.anc_toponyms = {}

    # global resolution: name -> geoname
    self.default_senses = {}
    self.selected_senses = {}
    self.api_selected_senses = {}

  def positions(self, toponym):
    if toponym in self.gaz_toponyms:
      return self.gaz_toponyms[toponym]
    if toponym in self.ner_toponyms:
      return self.ner_toponyms[toponym]
    if toponym in self.demonyms:
      return self.demonyms[toponym]
    if toponym in self.anc_toponyms:
      return self.anc_toponyms[toponym]
    return []


class TreeNode:

  toponyms = {}  # toponym: GeoName
  children = {}  # key: TreeNode
  mentions = 0

  def __init__(self, key, parent):
    self.key = key
    self.parent = parent

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

  def add(self, toponym, geoname, positions):
    self.toponyms[toponym] = geoname
    self.mentions += len(positions)

  def topo_counts(self):
    counts = []
    node = self
    while node != None:
      counts.append(len(node.toponyms))
      node = node.parent
    return counts

  def branch_mentions(self):
    mentions = 0
    node = self
    while node != None:
      mentions += node.mentions
      node = node.parent
    return mentions

