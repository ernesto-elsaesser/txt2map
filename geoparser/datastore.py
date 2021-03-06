import os
import csv
import json
import sqlite3
import pickle
from .util import GeoUtil
from .geonames import GeoName, GeoNamesAPI
from .osm import OSMElement, OverpassAPI


class Datastore:

  cache_dir = 'cache'
  geonames_search_classes = ['P', 'A', 'L', 'T', 'H', 'V']
  osm_search_dist = 15 # km
  osm_exclusions = ['shop', 'power', 'office', 'cuisine']
  osm_name_min_length = 4

  geonames = {}
  hierarchies = {}
  search_results = {}

  @staticmethod
  def get_geoname(geoname_id):
    if geoname_id in Datastore.geonames:
      return Datastore.geonames[geoname_id]
    db = Datastore._geonames_db()
    geoname = db.get_geoname(geoname_id)
    if geoname == None:
      geoname = GeoNamesAPI.get_geoname(geoname_id)
      db.store_geoname(geoname)
    Datastore.geonames[geoname_id] = geoname
    return geoname

  @staticmethod
  def search_geonames(name):
    if name in Datastore.search_results:
      return Datastore.search_results[name]
    db = Datastore._geonames_db()
    results = db.get_search(name)
    if results == None:
      classes = Datastore.geonames_search_classes
      results = GeoNamesAPI.search(name, classes)
      results = [g for g in results if g.id != 6295630] # remove Earth
      db.store_search(name, results)
    Datastore.search_results[name] = results
    return results

  @staticmethod
  def get_hierarchy(geoname_id):
    if geoname_id in Datastore.hierarchies:
      return Datastore.hierarchies[geoname_id]
    db = Datastore._geonames_db()
    hierarchy = db.get_hierarchy(geoname_id)
    if hierarchy == None:
      hierarchy = GeoNamesAPI.get_hierarchy(geoname_id)[1:]  # skip Earth
      db.store_hierarchy(hierarchy)
    Datastore.hierarchies[geoname_id] = hierarchy
    return hierarchy

  @staticmethod
  def get_children(geoname_id):
    db = Datastore._geonames_db()
    children = db.get_children(geoname_id)
    if children == None:
      children = GeoNamesAPI.get_children(geoname_id)
      db.store_children(geoname_id, children)
    return children
  
  @staticmethod
  def _geonames_db():
    db_path = Datastore._data_path('geonames', 'db', cache=True)
    exists = os.path.exists(db_path)
    sqlite_db = sqlite3.connect(db_path)
    geonames_db = GeoNamesDatabase(sqlite_db)
    if not exists:
      geonames_db.create_tables()
    return geonames_db

  @staticmethod
  def load_osm_database(geoname):
    search_dist = Datastore.osm_search_dist
    db_name = f'{geoname.id}-{search_dist}km'
    db_path = Datastore._data_path(db_name, 'db', cache=True)
    is_cached = os.path.exists(db_path)
    if is_cached and os.stat(db_path).st_size == 0:
      # inconsistent database state
      os.remove(db_path) 
      is_cached = False
    sqlite_db = sqlite3.connect(db_path)
    osm_db = OSMDatabase(sqlite_db)

    if not is_cached:
      print(f'lres - requesting OSM data for {geoname} ...')
      bbox = GeoUtil.bounding_box(geoname.lat, geoname.lon, search_dist)
      csv_reader = OverpassAPI.load_names_in_bounding_box(bbox, Datastore.osm_exclusions)
      name_count = Datastore._store_osm_data(osm_db, csv_reader, 1, [2, 3, 4, 5, 6])

    return osm_db

  @staticmethod
  def _store_osm_data(osm_db, csv_reader, type_col, name_cols):
    osm_db.create_tables()
    min_match_len = Datastore.osm_name_min_length

    col_num = len(name_cols) + 2
    name_count = 0
    for row in csv_reader:
      if len(row) != col_num:
        continue
      type_name = row[type_col]
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        if len(name) >= min_match_len:
          name_count += osm_db.insert_element(name, type_name, row[0])

    osm_db.commit_changes()
    return name_count

  @staticmethod
  def load_osm_geometries(elements):
    cache_key = 'geometries'
    if Datastore.data_available(cache_key, in_cache=True):
      cache = Datastore.load_data(cache_key, from_cache=True)
    else:
      cache = {}

    geometries = {'node': {}, 'way': {}, 'relation': {}}

    not_cached = []
    for e in elements:
      if e.reference in cache:
        geometries[e.type_name][e.id] = cache[e.reference]
      else:
        not_cached.append(e)

    if len(not_cached) > 0:
      data = OverpassAPI.load_geometries(not_cached)
      for d in data:
        type_name = d['type']
        el_id = d['id']
        reference = f'{type_name}/{el_id}'
        if type_name == 'node':
          geometry = [d['lat'], d['lon']]
        else:
          b = d['bounds']
          geometry = [b['minlat'], b['minlon'], b['maxlat'], b['maxlon']]
        cache[reference] = geometry
        geometries[type_name][el_id] = geometry

    Datastore.save_data(cache_key, cache, to_cache=True)

    return geometries

  @staticmethod
  def save_object(key, model, to_cache=False):
    model_path = Datastore._data_path(key, 'pickle', to_cache)
    with open(model_path, 'wb') as f:
      pickle.dump(model, f)

  @staticmethod
  def load_object(key, from_cache=False):
    model_path = Datastore._data_path(key, 'pickle', from_cache)
    with open(model_path, 'rb') as f:
      return pickle.load(f)
  
  @staticmethod
  def load_data(key, from_cache=False):
    file_path = Datastore._data_path(key, 'json', from_cache)
    with open(file_path, 'r') as f:
      data = json.load(f)
    return data

  @staticmethod
  def save_data(key, data, to_cache=False):
    file_path = Datastore._data_path(key, 'json', to_cache)
    with open(file_path, 'w') as f:
      json.dump(data, f)

  @staticmethod
  def data_available(key, in_cache=False):
    file_path = Datastore._data_path(key, 'json', in_cache)
    return os.path.exists(file_path)

  @staticmethod
  def _data_path(file_name, file_ext, cache):
    if cache:
      data_dir = Datastore.cache_dir
    else:
      dirname = os.path.dirname(__file__)
      data_dir = f'{dirname}/data'

    if not os.path.exists(data_dir):
      os.mkdir(data_dir)
    return f'{data_dir}/{file_name}.{file_ext}'


class Database:

  def __init__(self, sqlite_db):
    self.db = sqlite_db
    self.cursor = sqlite_db.cursor()

  def __del__(self):
    self.db.close()

  def commit_changes(self):
    self.db.commit()
  
  def initialize(self, statements):
    for s in statements:
      self.cursor.execute(s)
    self.commit_changes()


class GeoNamesDatabase(Database):

  def create_tables(self):
    self.initialize(
        ['CREATE TABLE geonames (geoname_id INT UNIQUE, name TEXT, population INT, lat REAL, lng REAL, fcl CHAR(1), fcode VARCHAR(10), cc CHAR(2), adm1 TEXT, toponame TEXT)',
        'CREATE TABLE search (name TEXT UNIQUE, result_ids TEXT)',
        'CREATE TABLE hierarchy (geoname_id INT UNIQUE, ancestor_ids TEXT)',
        'CREATE TABLE children (geoname_id INT UNIQUE, child_ids TEXT)'])

  def get_search(self, name):
    self.cursor.execute('SELECT result_ids FROM search WHERE name = ?',
                        (name, ))
    row = self.cursor.fetchone()
    return self._resolve_ids(row)

  def store_search(self, name, geonames):
    result_ids = ','.join(str(g.id) for g in geonames)
    try:
      self.cursor.execute('INSERT INTO search VALUES (?, ?)',
                        (name, result_ids))
    except:
      pass
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
    try:
      self.cursor.execute('INSERT INTO hierarchy VALUES (?, ?)',
                        (geoname_id, ancestor_ids))
    except:
      pass
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
    try:
      self.cursor.execute('INSERT INTO children VALUES (?, ?)',
                        (geoname_id, child_ids))
    except:
      pass
    for geoname in geonames:
      self.store_geoname(geoname)
    self.commit_changes()

  def _resolve_ids(self, row):
    if row == None:
      return None
    if row[0] == '':
      return []
    geonames = [self.get_geoname(int(s)) for s in row[0].split(',')]
    if None in geonames:
      return None
    else:
      return geonames

  def get_geoname(self, geoname_id):
    self.cursor.execute('SELECT * FROM geonames WHERE geoname_id = ?',
                        (geoname_id, ))
    row = self.cursor.fetchone()
    return None if row == None else GeoName(row=row)

  def store_geoname(self, geoname):
    g = geoname
    try:
      self.cursor.execute('INSERT INTO geonames VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                          (g.id, g.name, g.population, g.lat, g.lon,
                           g.fcl, g.fcode, g.cc, g.adm1, g.toponym_name))
      self.commit_changes()
    except sqlite3.Error:
      pass

    
class OSMDatabase(Database):

  def create_tables(self):
    self.initialize(
        ['CREATE TABLE names (name VARCHAR(100) NOT NULL UNIQUE)',
        'CREATE INDEX names_index ON names(name)',
        'CREATE TABLE osm (ref BIGINT NOT NULL, names_rowid INTEGER NOT NULL, type_code TINYINT NOT NULL)',
        'CREATE INDEX osm_index ON osm(names_rowid)'])

  def insert_element(self, name, type_name, element_id):
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
    type_code = OSMElement.type_names.index(type_name)
    self.cursor.execute('INSERT INTO osm VALUES(?, ?, ?)',
                        (element_id, rowid, type_code))
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
      element = OSMElement(row[1], row[0])
      elements.append(element)
    return elements