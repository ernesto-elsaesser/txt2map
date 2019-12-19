import os
import requests
import json
import sqlite3
from .model import GeoName
from .database import GeoNamesDatabase


class GeoNamesCache:

  def __init__(self, cache_dir='cache'):
    self.db_path = cache_dir + '/geonames.db'
    if not os.path.exists(self.db_path):
      self.get_db().create_tables()

  def get_db(self):
    db = sqlite3.connect(self.db_path)
    return GeoNamesDatabase(db)

  def get(self, geoname_id):
    db = self.get_db()
    geoname = db.get_geoname(geoname_id)
    if geoname == None:
      geoname = GeoNamesAPI.get_geoname(geoname_id)
      db.store_geoname(geoname)
    return geoname

  def search(self, name):
    db = self.get_db()
    results = db.get_search(name)
    if results == None:
      results = GeoNamesAPI.search(name)
      results = [g for g in results if g.id != 6295630] # remove Earth
      db.store_search(name, results)
    return results

  def get_hierarchy(self, geoname_id):
    db = self.get_db()
    hierarchy = db.get_hierarchy(geoname_id)
    if hierarchy == None:
      hierarchy = GeoNamesAPI.get_hierarchy(geoname_id)[1:]  # skip Earth
      db.store_hierarchy(hierarchy)
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
  def search(name):
    params = [('q', name)]
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
