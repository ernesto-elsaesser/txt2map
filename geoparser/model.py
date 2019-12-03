import sqlite3

class GeoName:

  # data: dict
  # row: tupel
  def __init__(self, data=None, row=None):
    if data != None:
      self.id = data['geonameId']
      self.name = data['name']
      self.population = data['population']
      self.lat = float(data['lat'])
      self.lng = float(data['lng'])
      self.cc = '-' if 'countryCode' not in data else data['countryCode']
      self.adm1 = '-' if 'adminCode1' not in data else data['adminCode1']
      if 'fcode' in data:
        self.is_city = data['fcode'].startswith('PP')
      else:
        self.is_city = False
      #self.fclass = data['fcl']
    else:
      self.id = row[0]
      self.name = row[1]
      self.population = row[2]
      self.is_city = row[3]
      self.lat = row[4]
      self.lng = row[5]
      self.cc = row[6]
      self.adm1 = row[7]

  def __repr__(self):
    prefix = '*' if self.is_city else ''
    return f'{prefix}{self.name}, {self.cc}-{self.adm1}'


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
  # hierarchy: [GeoName]
  # mentioned_ancestors: [str]
  def __init__(self, toponym, geoname, hierarchy, mentioned_ancestors):
    self.name = toponym.name
    self.positions = toponym.positions
    self.geoname = geoname
    self.hierarchy = hierarchy
    self.mentioned_ancestors = mentioned_ancestors

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


class GeoNamesDatabase:

  def __init__(self, sqlite_db):
    self.db = sqlite_db
    self.cursor = sqlite_db.cursor()

  def __del__(self):
    self.db.close()

  def create_tables(self):
    self.cursor.execute(
        '''CREATE TABLE geonames (
          geoname_id INT UNIQUE, 
          name TEXT,
          population INT,
          is_city BOOLEAN,
          lat REAL,
          lng REAL,
          cc CHAR(2),
          adm1 TEXT)''')
    self.cursor.execute(
        'CREATE TABLE hierarchy (geoname_id INT UNIQUE, ancestor_ids TEXT)')
    self.cursor.execute(
        'CREATE TABLE search (name UNIQUE, result_ids TEXT)')
    self.db.commit()

  def get_search(self, name):
    self.cursor.execute('SELECT result_ids FROM search WHERE name = ?',
                        (name, ))
    row = self.cursor.fetchone()
    return None if row == None else self._resolve_ids(row[0])

  def store_search(self, name, geonames):
    result_ids = ','.join(str(g.id) for g in geonames)
    self.cursor.execute('INSERT INTO search VALUES (?, ?)',
                        (name, result_ids))
    for geoname in geonames:
      self.store_geoname(geoname)
    self.db.commit()

  def get_hierarchy(self, geoname_id):
    self.cursor.execute('SELECT ancestor_ids FROM hierarchy WHERE geoname_id = ?',
                        (geoname_id, ))
    row = self.cursor.fetchone()
    return None if row == None else self._resolve_ids(row[0])

  def store_hierarchy(self, geonames):
    geoname_id = geonames[-1].id
    ancestor_ids = ','.join(str(g.id) for g in geonames)
    self.cursor.execute('INSERT INTO hierarchy VALUES (?, ?)',
                        (geoname_id, ancestor_ids))
    for geoname in geonames:
      self.store_geoname(geoname)
    self.db.commit()

  def _resolve_ids(self, id_str):
    return [self.get_geoname(int(s)) for s in id_str.split(',')]

  def get_geoname(self, geoname_id):
    self.cursor.execute('SELECT * FROM geonames WHERE geoname_id = ?',
                        (geoname_id, ))
    row = self.cursor.fetchone()
    return None if row == None else GeoName(row=row)

  def store_geoname(self, geoname):
    g = geoname
    try:
      self.cursor.execute('INSERT INTO geonames VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                          (g.id, g.name, g.population, g.is_city, 
                          g.lat, g.lng, g.cc, g.adm1))
      self.db.commit()
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
