import os
import requests
import csv
import json
import io
import sqlite3
from .database import OSMDatabase
from .geo import GeoUtil
from .matcher import NameMatcher


class OSMLoader:

  def __init__(self, cache_dir, search_dist):
    self.cache_dir = cache_dir
    self.search_dist = search_dist
    self.matcher = NameMatcher([], 4, True)

  def annotate_local_names(self, geoname, doc, suffix):
    if self.search_dist == 0:
      return

    group_id = f'loc_{suffix}_{geoname.id}'
    db = self._load_database(geoname)
    self.matcher.recognize_names(doc, group_id, lambda p: db.find_names(p))

    for pos, phrase, _, db_name in doc.iter('rec', select=group_id):
      data = db.get_elements(db_name)
      doc.annotate('res', pos, phrase, group_id, data)

  def _load_database(self, geoname):
    file_path = f'{self.cache_dir}/{geoname.id}-{self.search_dist}km.db'
    is_cached = os.path.exists(file_path)
    db = sqlite3.connect(file_path)
    osm_db = OSMDatabase(db)

    if not is_cached:
      print(f'requesting OSM data for {geoname} ...')
      box = GeoUtil.bounding_box(geoname.lat, geoname.lon, self.search_dist)
      csv_reader = OverpassAPI.load_names_in_bounding_box(box)
      name_count = self._store_data(osm_db, csv_reader, 1, [2, 3, 4, 5])
      print(f'created database with {name_count} names.')

    return osm_db

  def _store_data(self, osm_db, csv_reader, type_col, name_cols):
    osm_db.create_tables()

    col_num = len(name_cols) + 2
    name_count = 0
    for row in csv_reader:
      if len(row) != col_num:
        continue
      type_name = row[type_col]
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        name_count += osm_db.insert_element(name, type_name, row[0])

    osm_db.commit_changes()
    return name_count

  def load_geometries(self, elements):
    short_refs = [e[0][0] + str(e[1]) for e in elements]
    max_ref = max(short_refs)
    num = len(elements) - 1
    file_path = f'{self.cache_dir}/{max_ref}+{num}.json'
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
  def load_names_in_bounding_box(bounding_box, excluded_keys=['shop', 'power', 'office', 'cuisine']):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "ref"; false)]; ('
    exclusions =  ''.join('[!"' + e + '"]' for e in excluded_keys)
    bbox = ','.join(map(str, bounding_box))
    query += f'node["name"]{exclusions}({bbox}); '
    query += f'way["name"]{exclusions}({bbox}); '
    query += f'rel["name"]{exclusions}({bbox}); '
    query += f'way[!"name"]["ref"]({bbox}); ' # include highway names
    query += '); out qt;'
    response = OverpassAPI.post_query(query)
    csv_input = io.StringIO(response.text, newline=None) # universal newlines mode
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
