import os
import requests
import csv
import json
import io
import sqlite3
from .database import Database
from .util import GeoUtil
from .matcher import NameMatcher
from .config import Config


class OSMLoader:

  @staticmethod
  def load_database(geonames):
    cache_dir = Config.cache_dir
    if not os.path.exists(cache_dir):
      os.mkdir(cache_dir)

    search_dist = Config.local_search_dist
    sorted_ids = sorted(str(g.id) for g in geonames)
    id_str = '-'.join(sorted_ids)
    file_path = f'{cache_dir}/{id_str}-{search_dist}km.db'
    is_cached = os.path.exists(file_path)
    db = sqlite3.connect(file_path)
    osm_db = OSMDatabase(db)

    if not is_cached:
      print(f'requesting OSM data for {geonames} ...')
      def bbox(g): return GeoUtil.bounding_box(g.lat, g.lon, search_dist)
      boxes = [bbox(g) for g in geonames]
      csv_reader = OverpassAPI.load_names_in_bounding_boxes(boxes)
      name_count = OSMLoader._store_data(osm_db, csv_reader, 1, [2, 3, 4, 5])
      print(f'created database with {name_count} names.')

    return osm_db

  @staticmethod
  def _store_data(osm_db, csv_reader, type_col, name_cols):
    osm_db.create_tables()
    min_match_len = Config.local_match_min_len

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
  def load_geometries(elements):
    short_refs = [e[0][0] + str(e[1]) for e in elements]
    max_ref = max(short_refs)
    num = len(elements) - 1
    cache_dir = Config.cache_dir
    file_path = f'{cache_dir}/{max_ref}+{num}.json'
    is_cached = os.path.exists(file_path)

    if is_cached:
      with open(file_path, 'r') as f:
        json_str = f.read()
      json_data = json.loads(json_str)
    else:
      osm_json = OverpassAPI.load_geometries(elements)
      json_data = osm_json['elements']
      with open(file_path, 'w') as f:
        json_str = json.dumps(json_data)
        f.write(json_str)

    return json_data


class OverpassAPI:

  @staticmethod
  def load_names_in_bounding_boxes(bounding_boxes):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "ref"; false)]; ('
    excl_keys = Config.local_osm_exclusions
    exclusions = ''.join('[!"' + e + '"]' for e in excl_keys)
    for bounding_box in bounding_boxes:
      bbox = ','.join(map(str, bounding_box))
      query += f'node["name"]{exclusions}({bbox}); '
      query += f'way["name"]{exclusions}({bbox}); '
      query += f'rel["name"]{exclusions}({bbox}); '
      query += f'way[!"name"]["ref"]({bbox}); '  # include highway names
    query += '); out qt;'
    response = OverpassAPI.post_query(query)
    # universal newlines mode
    csv_input = io.StringIO(response.text, newline=None)
    reader = csv.reader(csv_input, delimiter='\t')
    return reader

  @staticmethod
  def load_geometries(elements):
    query = '[out:json]; ('
    for e in elements:
      query += f'{e[0]}({e[1]}); '
    query += '); out geom;'
    response = OverpassAPI.post_query(query)
    return response.json()
    
  @staticmethod
  def post_query(query):
    url = 'http://overpass-api.de/api/interpreter'
    response = requests.post(url=url, data=query)
    response.encoding = 'utf-8'
    return response


class OSMDatabase(Database):

  type_names = ['node', 'way', 'relation']

  def create_tables(self):
    self.cursor.execute(
        'CREATE TABLE names (name VARCHAR(100) NOT NULL UNIQUE)')
    self.cursor.execute('CREATE INDEX names_index ON names(name)')
    self.cursor.execute(
        'CREATE TABLE osm (ref BIGINT NOT NULL, names_rowid INTEGER NOT NULL, type_code TINYINT NOT NULL)')
    self.cursor.execute('CREATE INDEX osm_index ON osm(names_rowid)')
    self.commit_changes()

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
    type_code = self.type_names.index(type_name)
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
      type_name = self.type_names[row[1]]
      elements.append([type_name, row[0]])
    return elements
