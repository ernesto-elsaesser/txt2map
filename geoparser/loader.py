import os
import logging
import sqlite3
import json
from osm2geojson import json2geojson
from .model import HierarchyDatabase, OSMElement, OSMDatabase
from .geo import GeoUtil
from .geonames import GeoNamesAPI
from .overpass import OverpassAPI

class DataLoader:

  def __init__(self, cache_dir='cache'):
    self.cache_dir = cache_dir
    if not os.path.exists(self.cache_dir):
      os.mkdir(self.cache_dir)
    self.hierarchy_db_path = cache_dir + '/hierarchies.db'
    if not os.path.exists(self.hierarchy_db_path):
      self.create_hierarchy_db()

  def create_hierarchy_db(self):
    db = sqlite3.connect(self.hierarchy_db_path)
    hierarchy_db = HierarchyDatabase(db)
    hierarchy_db.create_tables()
    hierarchy_db.commit_changes()

  def get_hierarchy(self, geoname_id):
    db = sqlite3.connect(self.hierarchy_db_path)
    hierarchy_db = HierarchyDatabase(db)
    hierarchy = hierarchy_db.get_hierarchy(geoname_id)
    if hierarchy == None:
      geonames = GeoNamesAPI.get_hierarchy(geoname_id)[1:] # skip Earth
      hierarchy = [(g.id, g.name) for g in geonames]
      hierarchy_db.store_hierarchy(hierarchy)
      hierarchy_db.commit_changes()
    return hierarchy

  def get_geoname_geometry(self, geoname):
    dirname = os.path.dirname(__file__)
    db = sqlite3.connect(dirname + '/shapes.db')
    cursor = db.cursor()
    cursor.execute('SELECT geojson FROM shapes WHERE geoname_id = ?', (geoname.id, ))
    row = cursor.fetchone()
    db.close()
    if row == None:
      return GeoUtil.make_point(geoname.lat, geoname.lng)
    return json.loads(row[0])

  def load_osm_database(self, cluster, search_dist):
    logging.info('loading OSM data ...')
    sorted_ids = sorted(str(id) for id in cluster.city_ids())
    cluster_id = '-'.join(sorted_ids)
    file_path = f'{self.cache_dir}/{cluster_id}-{search_dist}km.db'
    is_cached = os.path.exists(file_path)
    db = sqlite3.connect(file_path)
    osm_db = OSMDatabase(db)

    if not is_cached:
      def bbox(g): return GeoUtil.bounding_box(g.lat, g.lng, search_dist)
      boxes = [bbox(g) for g in cluster.city_geonames]
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
