import logging
import os
import requests
import csv
import json
import io
import sqlite3
from .model import OSMElement
from .database import OSMDatabase
from .geo import GeoUtil
from .matcher import NameMatcher


class OSMLoader:

  def __init__(self, cache_dir, search_dist):
    self.cache_dir = cache_dir
    self.search_dist = search_dist
    self.matcher = NameMatcher(True, True, 4, True)

  def find_local_matches(self, layer, doc):
    if self.search_dist == 0:
      return

    db = self._load_database(layer.anchor_points)
    results = self.matcher.find_names(doc, lambda p: db.find_names(p))

    for phrase, completions in results.items():
      positions = [c.start for c in completions]
      elements = []
      for c in completions:
        for e in db.get_elements(c.db_name): 
          elements.append(e.reference())
      layer.toponyms[phrase] = positions
      layer.osm_elements[phrase] = elements

  def _load_database(self, geonames):
    sorted_ids = sorted(str(g.id) for g in geonames)
    cluster_id = '-'.join(sorted_ids)
    file_path = f'{self.cache_dir}/{cluster_id}-{self.search_dist}km.db'
    is_cached = os.path.exists(file_path)
    db = sqlite3.connect(file_path)
    osm_db = OSMDatabase(db)

    if not is_cached:
      logging.info('requesting OSM data for %s ...', str(geonames))
      def bbox(g): return GeoUtil.bounding_box(g.lat, g.lon, self.search_dist)
      boxes = [bbox(g) for g in geonames]
      csv_reader = OverpassAPI.load_names_in_bounding_boxes(boxes)
      name_count = self._store_data(osm_db, csv_reader, 1, [2, 3, 4, 5])
      logging.info('created database with %d unique names.', name_count)

    return osm_db

  def _store_data(self, osm_db, csv_reader, type_col, name_cols):
    osm_db.create_tables()

    col_num = len(name_cols) + 2
    name_count = 0
    for row in csv_reader:
      if len(row) != col_num:
        continue
      element = OSMElement(row[0], row[type_col])
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        name_count += osm_db.insert_element(name, element)

    osm_db.commit_changes()
    return name_count

  def load_geometries(self, elements):
    max_ref = max(e.short_ref() for e in elements)
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
  def load_names_in_bounding_boxes(bounding_boxes, excluded_keys=['shop', 'power', 'office', 'cuisine']):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "ref"; false)]; ('
    exclusions =  ''.join('[!"' + e + '"]' for e in excluded_keys)
    for bounding_box in bounding_boxes:
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
    for elem in elements:
      query += f'{elem.element_type}({elem.id}); '
    query += '); out geom;'
    response = OverpassAPI.post_query(query)
    return response.json()
    
  @staticmethod
  def post_query(query):
    url = 'http://overpass-api.de/api/interpreter'
    response = requests.post(url=url, data=query)
    response.encoding = 'utf-8'
    return response
