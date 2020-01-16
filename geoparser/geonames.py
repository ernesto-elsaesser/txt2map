import os
import requests
import json
import sqlite3
from .database import Database
from .config import Config


class GeoNamesCache:

  geonames = {}
  hierarchies = {}
  search_results = {}

  def get_db(self):
    cache_dir = Config.cache_dir
    if not os.path.exists(cache_dir):
      os.mkdir(cache_dir)
    db_path = cache_dir + '/geonames.db'
    exists = os.path.exists(db_path)
    sqlite_db = sqlite3.connect(db_path)
    db = GeoNamesDatabase(sqlite_db)
    if not exists:
      db.create_tables()
    return db

  def get(self, geoname_id):
    if geoname_id in self.geonames:
      return self.geonames[geoname_id]
    db = self.get_db()
    geoname = db.get_geoname(geoname_id)
    if geoname == None:
      geoname = GeoNamesAPI.get_geoname(geoname_id)
      db.store_geoname(geoname)
    self.geonames[geoname_id] = geoname
    return geoname

  def search(self, name):
    if name in self.search_results:
      return self.search_results[name]
    db = self.get_db()
    results = db.get_search(name)
    if results == None:
      classes = Config.geonames_search_classes
      results = GeoNamesAPI.search(name, classes)
      results = [g for g in results if g.id != 6295630] # remove Earth
      db.store_search(name, results)
    self.search_results[name] = results
    return results

  def get_hierarchy(self, geoname_id):
    if geoname_id in self.hierarchies:
      return self.hierarchies[geoname_id]
    db = self.get_db()
    hierarchy = db.get_hierarchy(geoname_id)
    if hierarchy == None:
      hierarchy = GeoNamesAPI.get_hierarchy(geoname_id)[1:]  # skip Earth
      db.store_hierarchy(hierarchy)
    self.hierarchies[geoname_id] = hierarchy
    return hierarchy

  def get_children(self, geoname_id):
    db = self.get_db()
    children = db.get_children(geoname_id)
    if children == None:
      children = GeoNamesAPI.get_children(geoname_id)
      db.store_children(geoname_id, children)
    return children


class GeoNamesAPI:

  @staticmethod
  def search(name, feature_classes):
    params = [('q', name)]
    for fcl in feature_classes:
      params.append(('featureClass', fcl))
    json_data = GeoNamesAPI.get_json('search', params)
    if not 'geonames' in json_data:
      return []
    json_array = json_data['geonames']
    return list(map(GeoName, json_array))

  @staticmethod
  def get_hierarchy(id):
    params = [('geonameId', id)]
    json_data = GeoNamesAPI.get_json('hierarchy', params)
    json_array = json_data['geonames']
    return list(map(GeoName, json_array))

  @staticmethod
  def get_children(id):
    params = [('geonameId', id)]
    json_data = GeoNamesAPI.get_json('children', params)
    if not 'geonames' in json_data:
      return []
    json_array = json_data['geonames']
    return list(map(GeoName, json_array))

  @staticmethod
  def get_geoname(id):
    params = [('geonameId', id)]
    json_data = GeoNamesAPI.get_json('get', params)
    return GeoName(json_data)

  @staticmethod
  def get_json(endpoint, params):
    url = f'http://api.geonames.org/{endpoint}JSON?username=map2txt'
    for key, value in params:
      url += f'&{key}={value}'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return res.json()


class GeoNamesDatabase(Database):

  def create_tables(self):
    self.cursor.execute(
        '''CREATE TABLE geonames (
          geoname_id INT UNIQUE, 
          name TEXT,
          population INT,
          lat REAL,
          lng REAL,
          fcl CHAR(1),
          fcode VARCHAR(10),
          cc CHAR(2),
          adm1 TEXT, 
          toponame TEXT)''')
    self.cursor.execute(
        'CREATE TABLE search (name TEXT UNIQUE, result_ids TEXT)')
    self.cursor.execute(
        'CREATE TABLE hierarchy (geoname_id INT UNIQUE, ancestor_ids TEXT)')
    self.cursor.execute(
        'CREATE TABLE children (geoname_id INT UNIQUE, child_ids TEXT)')
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


class GeoName:

  def __init__(self, data=None, row=None):
    if data != None:
      self.id = data['geonameId']
      self.name = data['name']
      self.population = data['population']
      self.lat = float(data['lat'])
      self.lon = float(data['lng'])
      self.fcl = '-' if 'fcl' not in data else data['fcl']
      self.fcode = '-' if 'fcode' not in data else data['fcode']
      self.cc = '-' if 'countryCode' not in data else data['countryCode']
      self.adm1 = '-' if 'adminCode1' not in data else data['adminCode1']
      self.toponym_name = data['toponymName']
      # not cached:
      if 'asciiName' in data:
        self.asciiname = data['asciiName']
      if 'alternateNames' in data:
        self.altnames = data['alternateNames']
      if 'wikipediaURL' in data:
        self.wiki_url = data['wikipediaURL']
      else:
        self.wiki_url = None
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
      self.toponym_name = row[9]

    self.is_city = self.fcl == 'P'
    self.is_country = self.fcode.startswith('PCL')
    self.is_continent = self.fcode == 'CONT'
    self.is_ocean = self.fcode == 'OCN'

  def region(self):
    return f'{self.cc}-{self.adm1}'

  def __repr__(self):
    return f'{self.toponym_name}, {self.adm1}, {self.cc} [{self.fcode}]'
