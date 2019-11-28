import os
import logging
import sqlite3
import json
from geojson.geometry import Point
from osm2geojson import json2geojson
from .model import GeoName, GeoNameCandidate, OSMElement, OSMDatabase
from .geonames import GeoNamesAPI
from .overpass import OverpassAPI

class DataLoader:

  def __init__(self, cache_dir='cache'):
    self.cache_dir = cache_dir
    if not os.path.exists(self.cache_dir):
      os.mkdir(self.cache_dir)

  def load_geoname_hierarchy(self, geoname_id):
    file_path = f'{self.cache_dir}/{geoname_id}.json'
    is_cached = os.path.exists(file_path)

    if is_cached:
      with open(file_path, 'r', encoding='utf-8') as f:
        json_str = f.read()
      json_array = json.loads(json_str)
    else:
      json_data = GeoNamesAPI.get_hierarchy(geoname_id)
      json_array = json_data['geonames']
      json_str = json.dumps(json_array)
      with open(file_path, 'w', encoding='utf-8') as f:
        f.write(json_str)

    return list(map(lambda d: GeoName(data=d), json_array))

  def load_geoname_candidates(self, toponyms):
    logging.info('loading GeoNames data ...')
    toponym_names = [t.name for t in toponyms]
    for toponym in toponyms:
      json_data = GeoNamesAPI.search(toponym.name)
      if not 'geonames' in json_data:
        continue
      json_array = json_data['geonames']
      geonames = list(map(lambda d: GeoName(data=d), json_array))
      for geoname in geonames:
        hierarchy = self.load_geoname_hierarchy(geoname.id)
        hierarchy_names = set([g.name for g in hierarchy])
        if not geoname.name in toponym.name:
          hierarchy_names.add(toponym.name)
        mentions = self.count_candidate_mentions(hierarchy_names, toponym_names)
        candidate = GeoNameCandidate(hierarchy, mentions)
        toponym.candidates.append(candidate)

  def count_candidate_mentions(self, hierarchy_names, toponym_names):
    matched_names = set()
    for h_name in hierarchy_names:
      for t_name in toponym_names:
        if t_name in h_name or h_name in t_name:
          matched_names.add(t_name)
    return len(matched_names)

  def get_geoname_shape(self, geoname):
    dirname = os.path.dirname(__file__)
    db = sqlite3.connect(dirname + '/shapes.db')
    cursor = db.cursor()
    cursor.execute('SELECT geojson FROM shapes WHERE geoname_id = ?', (geoname.id, ))
    row = cursor.fetchone()
    db.close()
    if row == None:
      return Point(coordinates=[geoname.lng, geoname.lat])
    return json.loads(row[0])

  def load_osm_database(self, cluster):
    logging.info('loading OSM data ...')
    sorted_ids = sorted(str(id) for id in cluster.city_ids())
    cluster_id = '-'.join(sorted_ids)
    file_path = f'{self.cache_dir}/osm-{cluster_id}.db'
    is_cached = os.path.exists(file_path)
    db = sqlite3.connect(file_path)
    osm_db = OSMDatabase(db)

    if not is_cached:
      boxes = cluster.bounding_boxes()
      csv_reader = OverpassAPI.load_names_in_bounding_boxes(boxes)
      name_count = self.store_osm_data(osm_db, csv_reader, 1, [2, 3, 4, 5])
      logging.info('created database with %d unique names.', name_count)

    return osm_db

  def store_osm_data(self, osm_db, csv_reader, type_col, name_cols):
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

  def load_osm_geometries(self, osm_elements):
    json_response = OverpassAPI.load_geometries(osm_elements)
    return json2geojson(json_response)
