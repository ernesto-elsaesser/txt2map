
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


class ToponymMap:

  def __init__(self):
    self.names = {}

  def add(self, name, pos):
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


class ResolvedToponym:

  # name: str
  # positions: [int]
  # hierarchy: [GeoName]
  def __init__(self, name, positions, hierarchy):
    self.name = name
    self.positions = positions
    self.geoname = hierarchy[-1]
    self.hierarchy = hierarchy

  def __repr__(self):
    return ' > '.join(g.name for g in self.hierarchy)


class ToponymCluster:

  # toponyms: [ResolvedToponym]
  # cities: [ResolvedToponym]
  # anchor: ResolvedToponym
  def __init__(self, toponyms, cities, anchor):
    self.toponyms = toponyms
    self.cities = cities
    self.anchor = anchor
    self.city_geonames = [t.geoname for t in cities]
    self.size = len(toponyms)
    self.local_matches = []
    self.confidence = 0

  def city_ids(self):
    return [g.id for g in self.city_geonames]

  def population(self):
    return self.anchor.geoname.population

  def mentions(self):
    return sum(len(t.positions) for t in self.toponyms)

  def path(self):
    return [g.name for g in self.anchor.hierarchy]

  def __repr__(self):
    path = self.path()
    cities = sorted(
        self.city_geonames, key=lambda g: g.population, reverse=True)
    repr_str = ' > '.join(path)
    for geoname in cities:
      if geoname.name != path[-1]:
        repr_str += ' + ' + geoname.name
    return repr_str


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
