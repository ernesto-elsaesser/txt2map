import sqlite3
from .model import GeoName, OSMElement

class Database:

  def __init__(self, sqlite_db):
    self.db = sqlite_db
    self.cursor = sqlite_db.cursor()

  def __del__(self):
    self.db.close()

  def commit_changes(self):
    self.db.commit()


class GeoNamesDatabase(Database):

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
        'CREATE TABLE search (name TEXT UNIQUE, result_ids TEXT)')
    self.cursor.execute(
        'CREATE TABLE hierarchy (geoname_id INT UNIQUE, ancestor_ids TEXT)')
    self.cursor.execute(
        'CREATE TABLE children (geoname_id INT UNIQUE, result_ids TEXT)')
    self.commit_changes()

  def get_search(self, name):
    self.cursor.execute('SELECT result_ids FROM search WHERE name = ?',
                        (name, ))
    row = self.cursor.fetchone()
    return self._resolve_ids(row)

  def store_search(self, name, geonames):
    result_ids = ','.join(str(g.id) for g in geonames)
    self.cursor.execute('INSERT INTO search VALUES (?, ?)',
                        (name, result_ids))
    for geoname in geonames:
      self.store_geoname(geoname)
    self.commit_changes()

  def get_hierarchy(self, geoname_id):
    self.cursor.execute('SELECT ancestor_ids FROM hierarchy WHERE geoname_id = ?',
                        (geoname_id, ))
    row = self.cursor.fetchone()
    return self._resolve_ids(row)

  def store_hierarchy(self, geonames):
    geoname_id = geonames[-1].id
    ancestor_ids = ','.join(str(g.id) for g in geonames)
    self.cursor.execute('INSERT INTO hierarchy VALUES (?, ?)',
                        (geoname_id, ancestor_ids))
    for geoname in geonames:
      self.store_geoname(geoname)
    self.commit_changes()

  def get_children(self, geoname_id):
    self.cursor.execute('SELECT child_ids FROM children WHERE geoname_id = ?',
                        (geoname_id, ))
    row = self.cursor.fetchone()
    return self._resolve_ids(row)

  def store_children(self, geoname_id, geonames):
    child_ids = ','.join(str(g.id) for g in geonames)
    self.cursor.execute('INSERT INTO children VALUES (?, ?)',
                        (geoname_id, child_ids))
    for geoname in geonames:
      self.store_geoname(geoname)
    self.commit_changes()

  def _resolve_ids(self, row):
    if row == None:
      return None
    if row[0] == '':
      return []
    return [self.get_geoname(int(s)) for s in row[0].split(',')]

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
      self.commit_changes()
    except sqlite3.Error:
      pass


class OSMDatabase(Database):

  def create_tables(self):
    self.cursor.execute(
        'CREATE TABLE names (name VARCHAR(100) NOT NULL UNIQUE)')
    self.cursor.execute('CREATE INDEX names_index ON names(name)')
    self.cursor.execute(
        'CREATE TABLE osm (ref BIGINT NOT NULL, names_rowid INTEGER NOT NULL, type_code TINYINT NOT NULL)')
    self.cursor.execute('CREATE INDEX osm_index ON osm(names_rowid)')
    self.commit_changes()

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
