
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


class Cluster:

  def __init__(self, key):
    self.key = key
    self.demonyms = []
    self.gaz_toponyms = []
    self.ner_toponyms = []
    self.anc_toponyms = []


class LocalLayer:

  def __init__(self, base, adm1, anchor_points, all_geonames):
    self.base = base
    self.adm1 = adm1
    self.anchor_points = anchor_points
    self.all_geonames = all_geonames
    self.confidence = 0

    # recognition: name -> positions
    self.toponyms = {}

    # resolution: name -> osm elements
    self.osm_elements = {}


class Document:

  def __init__(self, text):
    self.text = text + ' ' # allow matching of last word
    self.name_tokens = []
    self.local_layers = []

    # recognition: name -> positions
    self.demonyms = {}
    self.gaz_toponyms = {}
    self.ner_toponyms = {}
    self.anc_toponyms = {}

    # global resolution: name -> geoname
    self.default_senses = {}
    self.all_senses = {}
    self.selected_senses = {}
