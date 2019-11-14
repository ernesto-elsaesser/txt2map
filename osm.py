import requests
import csv
import logging
import os
from database import NameDatabase

class OSMDatabase(NameDatabase):

  ref_types = ['node', 'way', 'relation']

  def __init__(self, identifier):
    path = f'data/osm_{identifier}.db'
    self.data_exists = os.path.exists(path)
    super().__init__(path)

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

  def load_all_names(self, bounds_list, db):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name")]; ('

    for bounds in bounds_list:
      bbox = ','.join(map(str, bounds))
      query += f'node["name"][!"shop"]({bbox}); way["name"]({bbox}); rel["name"]({bbox}); '

    query += '); out qt;'
    return self.load(db, query, 1, [2, 3, 4, 5])

  def load(self, db, query, type_col, name_cols):
    csv_lines = self.fetch_data(query)
    logging.info('received %d lines.', len(csv_lines))
    reader = csv.reader(csv_lines, delimiter='\t')
    name_count = self.insert_data(db, reader, type_col, name_cols)
    db.commit_changes()
    logging.info('inserted %d unique names.', name_count)

  def fetch_data(self, query):
    res = requests.post(url=self.api_url, data=query)
    res.encoding = 'utf-8'
    return res.text.split('\n')[1:-1]

  def insert_data(self, db, reader, type_col, name_cols):
    name_count = 0
    for row in reader:
      ref = row[0]
      ref_type = row[type_col]
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        name_count += db.insert_ref(name, ref, ref_type)
    return name_count
