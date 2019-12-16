
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
    self.text = text
    self.names = {}
    self.anchors = {}

  def add_anchor(self, start, text):
    self.anchors[start] = text

  def add_toponym(self, name, pos):
    end = pos + len(name)

    all_positions = list(self.names.keys())
    for l in all_positions:
      r = l + len(self.names[l])
      if l <= pos and end <= r:  # already covered
        return
      elif pos <= l and r <= end: # covers previous
        del self.names[l]

    self.names[pos] = name

  def toponyms(self):
    return set(self.names.values())

  def is_annotated(self, pos):
    return pos in self.names

  def positions(self, name):
    return [p for p, n in self.names.items() if n == name]

  def first(self, name):
    return min(self.positions(name))

  def toponyms_in_window(self, left, right):
    return [n for p, n in self.names.items() if left < p < right]


class Candidate:

  # hierarchy: [GeoName]
  # geoname: GeoName
  # ancestors: [GeoName]
  def __init__(self, hierarchy):
    self.hierarchy = hierarchy
    self.geoname = hierarchy[-1]
    self.ancestors = hierarchy[:-1]

  def __repr__(self):
    return repr(self.geoname)


class ResolutionSet:

  # name: str
  # positions: [int]
  # candidates: [Candidate]
  # selected_idx: int
  # local_context GeoName?
  def __init__(self, name, positions, candidates):
    self.name = name
    self.positions = positions
    self.candidates = candidates
    self.selected_idx = 0
    self.local_context = None

  def selected(self):
    return self.candidates[self.selected_idx]

  def geoname(self):
    return self.selected().geoname

  def hierarchy(self):
    return self.selected().hierarchy

  def population(self):
    return self.geoname().population

  def __repr__(self):
    hierarchy = self.selected().hierarchy
    return ' > '.join(g.name for g in hierarchy)


class ToponymCluster:

  # sets: [ResolutionSet]
  # anchor: ResolutionSet
  # city_geonames: [GeoName]
  # size: int
  # local_matches: [OSMMatch]
  # confidence: float
  def __init__(self, sets, anchor):
    self.sets = sets
    self.local_contexts = [rn.local_context for rn in sets if rn.local_context != None]
    self.anchor = anchor
    self.size = len(sets)
    self.local_matches = []
    self.confidence = 0

  def population(self):
    return self.anchor.population()

  def mentions(self):
    return sum(len(rs.positions) for rs in self.sets)

  def path(self):
    return self.anchor.hierarchy()

  def __repr__(self):
    anchor_repr = repr(self.anchor)
    names = ','.join(rs.name for rs in self.sets)
    return f'{anchor_repr} ({names})'


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


class OSMMatch:

  # name: str
  # positions: [int]
  # elements: [OSMElement]
  def __init__(self, name, positions, elements):
    self.name = name
    self.positions = positions
    self.elements = elements

  def __repr__(self):
    return self.name
