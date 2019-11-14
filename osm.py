import requests
import csv
import logging
import os
import regex
import io
from database import NameDatabase

class OSMDatabase(NameDatabase):

  ref_types = ['node', 'way', 'relation']

  def create_tables(self):
    self.cursor.execute(
        'CREATE TABLE osm (ref BIGINT NOT NULL, names_rowid INTEGER NOT NULL, type_code TINYINT NOT NULL)')
    self.cursor.execute('CREATE INDEX osm_index ON osm(names_rowid)')
    super().create_tables()

  def insert_ref(self, name, ref, ref_type):
    (rowid, created) = self.insert_name(name)
    if rowid != None:
      type_code = self.ref_types.index(ref_type)
      self.cursor.execute('INSERT INTO osm VALUES(?, ?, ?)',
                          (ref, rowid, type_code))
    return 1 if created else 0

  def get_refs(self, name):
    rowid = self.get_rowid(name)
    self.cursor.execute(
        'SELECT ref,type_code FROM osm WHERE names_rowid = ?', (rowid, ))
    refs = [[], [], []]
    for row in self.cursor.fetchall():
      refs[row[1]].append(row[0])
    return refs


class OverpassClient:

  api_url = 'http://overpass-api.de/api/interpreter'

  def load_name_database(self, cluster):
    cluster_id = cluster.identifier()
    db_path = f'data/osm_{cluster_id}.db'
    data_cached = os.path.exists(db_path)
    
    if data_cached:
      db = OSMDatabase(db_path)
    else:
      logging.info('requesting data from OSM ...')
      query = self.query_for_cluster(cluster)
      res = requests.post(url=self.api_url, data=query)
      res.encoding = 'utf-8'
      (db, name_count) = self.create_database(db_path, res.text, 1, [2, 3, 4, 5])
      logging.info('created database with %d unique names.', name_count)

    return db

  def query_for_cluster(self, cluster):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name"; false)]; ('
    for bounds in cluster.clustered_bounds:
      bbox = ','.join(map(str, bounds))
      query += f'node["name"][!"shop"]({bbox}); way["name"]({bbox}); rel["name"]({bbox}); '
    query += '); out qt;'
    return query

  def create_database(self, db_path, csv_text, type_col, name_cols):
    csv_input = io.StringIO(csv_text, newline=None) # universal newlines mode
    reader = csv.reader(csv_input, delimiter='\t')
    db = OSMDatabase(db_path)
    db.create_tables()
    col_num = len(name_cols) + 2
    name_count = 0
    for row in reader:
      if len(row) != col_num:
        continue
      ref = row[0]
      ref_type = row[type_col]
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        name_count += db.insert_ref(name, ref, ref_type)
    db.commit_changes()
    return (db, name_count)
