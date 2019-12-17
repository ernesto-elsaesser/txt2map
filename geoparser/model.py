
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
      self.fcl = data['fcl']
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
  
  def region(self):
    return f'{self.cc}-{self.adm1}'

  def __repr__(self):
    return f'{self.name}, {self.adm1}, {self.cc} [{self.fcode}]'


class Document:

  def __init__(self, text):
    self.text = text + ' ' # allow matching of last word

    self.anchors = {}
    self.anchors_no_num = {}

    self.globals = {}
    self.geonames = {}
    self.locals = {}
    self.osm_elements = {}

  def add_anchor(self, start, text):
    self.anchors[start] = text
    self.anchors_no_num[start] = text

  def add_num_anchor(self, start, text):
    self.anchors[start] = text

  def get_anchors(self, with_num):
    return self.anchors if with_num else self.anchors_no_num

  def recognize_globally(self, toponym, positions):
    self.globals[toponym] = positions

  def resolve_globally(self, toponym, positions, geoname):
    self.recognize_globally(toponym, positions)
    self.geonames[toponym] = geoname

  def global_toponyms(self):
    return list(self.globals.keys())

  def resolve_locally(self, toponym, positions, osm_elements, path):
    key = ' > '.join(path)
    if key not in self.locals:
      self.locals[key] = {}
    self.locals[key][toponym] = positions
    if key not in self.osm_elements:
      self.osm_elements[key] = {}
    self.osm_elements[key][toponym] = osm_elements


class ToponymCluster:

  # toponyms: [str]
  # hierarchy: [GeoName]
  # local_context: [GeoName]
  # size: int
  # local_matches: [OSMMatch]
  # confidence: float
  def __init__(self, toponyms, hierarchy, local_context, mentions):
    self.toponyms = toponyms
    self.hierarchy = hierarchy
    self.local_context = local_context
    self.mentions = mentions
    self.anchor = hierarchy[-1]
    self.size = len(toponyms)
    self.local_matches = []
    self.confidence = 0

  def population(self):
    return self.anchor.population

  def path(self):
    return [g.name for g in self.hierarchy]

  def __repr__(self):
    path_str = ' > '.join(self.path())
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
