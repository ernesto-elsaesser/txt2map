import sqlite3

class GeoName:

  # data: JSON dictionary
  def __init__(self, data):
    self.id = data['geonameId']
    self.name = data['name']
    self.population = data['population']
    self.fclass = data['fcl']
    self.fcode = '-' if 'fcode' not in data else data['fcode']
    self.lat = float(data['lat'])
    self.lng = float(data['lng'])
    self.cc = '-' if 'countryCode' not in data else data['countryCode']
    self.adm1 = '-' if 'adminCode1' not in data else data['adminCode1']

    self.is_city = self.fcode.startswith('PP')

  def __repr__(self):
    return f'{self.name}, {self.cc} [{self.fcode}]'


class Toponym:

  # name: [GeoNameCandidate]
  # positions: [int]
  def __init__(self, name, positions):
    self.name = name
    self.positions = positions

  def __repr__(self):
    return self.name


class ResolvedToponym:

  # toponym: Toponym
  # geoname: GeoName
  # hierarchy: [(int, str)]
  # mentioned_ancestors: [str]
  def __init__(self, toponym, geoname, hierarchy, mentioned_ancestors):
    self.name = toponym.name
    self.positions = toponym.positions
    self.geoname = geoname
    self.hierarchy = hierarchy
    self.mentioned_ancestors = mentioned_ancestors

  def __repr__(self):
    return ' > '.join(n for _, n in self.hierarchy)


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

  def __repr__(self):
    hierarchy_names = [name for _, name in self.anchor.hierarchy]
    cities = sorted(
        self.city_geonames, key=lambda g: g.population, reverse=True)
    path = ' > '.join(hierarchy_names)
    for geoname in cities:
      if geoname.name != hierarchy_names[-1]:
        path += ' + ' + geoname.name
    return path


class HierarchyDatabase:

  def __init__(self, sqlite_db):
    self.db = sqlite_db
    self.cursor = sqlite_db.cursor()

  def __del__(self):
    self.db.close()

  def commit_changes(self):
    self.db.commit()

  def create_tables(self):
    self.cursor.execute('CREATE TABLE ancestors (geoname_id INT UNIQUE, ancestor_ids TEXT)')
    self.cursor.execute('CREATE TABLE names (geoname_id INT UNIQUE, name TEXT)')

  def get_hierarchy(self, geoname_id):
    self.cursor.execute('SELECT ancestor_ids FROM ancestors WHERE geoname_id = ?',
                        (geoname_id, ))
    row = self.cursor.fetchone()
    if row == None:
      return None
    ancestor_ids = map(int, row[0].split(','))
    hierarchy = []
    for id in ancestor_ids:
      name = self.get_name(id)
      hierarchy.append((id, name))
    return hierarchy

  def store_hierarchy(self, hierarchy):
    geoname_id = hierarchy[-1][0]
    ancestor_ids = ','.join(str(id) for id, _ in hierarchy)
    self.cursor.execute('INSERT INTO ancestors VALUES (?, ?)',
                        (geoname_id, ancestor_ids))
    for id, name in hierarchy:
      self.store_name(id, name)

  def get_name(self, geoname_id):
    self.cursor.execute('SELECT name FROM names WHERE geoname_id = ?',
                        (geoname_id, ))
    return self.cursor.fetchone()[0]

  def store_name(self, geoname_id, name):
    try:
        self.cursor.execute('INSERT INTO names VALUES (?, ?)',
                            (geoname_id, name))
    except sqlite3.Error:
      pass


class OSMElement:

  type_names = ['node', 'way', 'relation']

  # reference: int
  # element_type: 'node' or 'way' or 'relation'
  def __init__(self, reference, element_type):
    self.reference = reference
    self.element_type = element_type

  def __repr__(self):
    return f'{self.element_type}/{self.reference}'

  def url(self):
    return 'https://www.openstreetmap.org/' + str(self)

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


class OSMDatabase:

  def __init__(self, sqlite_db):
    self.db = sqlite_db
    self.cursor = sqlite_db.cursor()

  def __del__(self):
    self.db.close()

  def commit_changes(self):
    self.db.commit()

  def create_tables(self):
    self.cursor.execute(
        'CREATE TABLE names (name VARCHAR(100) NOT NULL UNIQUE)')
    self.cursor.execute('CREATE INDEX names_index ON names(name)')
    self.cursor.execute(
        'CREATE TABLE osm (ref BIGINT NOT NULL, names_rowid INTEGER NOT NULL, type_code TINYINT NOT NULL)')
    self.cursor.execute('CREATE INDEX osm_index ON osm(names_rowid)')

  def insert_element(self, name, element):
    if len(name) < 2:
      return 0
    first = name[0]
    if not first.isupper() and not first.isdigit():
      return 0
    inserted = 0
    try:
      self.cursor.execute('INSERT INTO names VALUES (?)', (name, ))
      rowid = self.cursor.lastrowid
      inserted = 1
    except sqlite3.Error:
      rowid = self.get_rowid(name)
    type_code = element.type_code()
    self.cursor.execute('INSERT INTO osm VALUES(?, ?, ?)',
                        (element.reference, rowid, type_code))
    return inserted

  def find_names(self, prefix):
    self.cursor.execute(
        'SELECT * FROM names WHERE name LIKE ?', (prefix + '%', ))
    return list(map(lambda r: r[0], self.cursor.fetchall()))

  def get_rowid(self, name):
    self.cursor.execute('SELECT rowid FROM names WHERE name = ?', (name, ))
    return self.cursor.fetchone()[0]

  def get_elements(self, name):
    rowid = self.get_rowid(name)
    self.cursor.execute(
        'SELECT ref,type_code FROM osm WHERE names_rowid = ?', (rowid, ))
    elements = []
    for row in self.cursor.fetchall():
      element_type = OSMElement.type_names[row[1]]
      element = OSMElement(row[0], element_type)
      elements.append(element)
    return elements
