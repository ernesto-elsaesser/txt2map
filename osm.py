import requests
import sqlite3
import csv
import logging
import os
import re
import io

class OSMMatch:

  def __init__(self, name, positions, refs):
    self.name = name
    self.positions = positions
    self.refs = refs

class OSMDatabase:

  ref_types = ['node', 'way', 'relation']

  def __init__(self, path):
    self.db = sqlite3.connect(path)
    self.cursor = self.db.cursor()
    #self.cursor.execute('PRAGMA case_sensitive_like = true')

  def __del__(self):
    self.db.close()

  def create_tables(self):
    self.cursor.execute(
        'CREATE TABLE names (name VARCHAR(100) NOT NULL UNIQUE)')
    self.cursor.execute('CREATE INDEX names_index ON names(name)')
    self.cursor.execute(
        'CREATE TABLE osm (ref BIGINT NOT NULL, names_rowid INTEGER NOT NULL, type_code TINYINT NOT NULL)')
    self.cursor.execute('CREATE INDEX osm_index ON osm(names_rowid)')
    self.commit_changes()

  def commit_changes(self):
    self.db.commit()

  def find_names(self, prefix):
    self.cursor.execute(
        'SELECT * FROM names WHERE name LIKE ?', (prefix + '%', ))
    return list(map(lambda r: r[0], self.cursor.fetchall()))

  def get_rowid(self, name):
    self.cursor.execute('SELECT rowid FROM names WHERE name = ?', (name, ))
    return self.cursor.fetchone()[0]

  def insert_ref(self, name, ref, ref_type):
    if name == '':
      return 0
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
    type_code = self.ref_types.index(ref_type)
    self.cursor.execute('INSERT INTO osm VALUES(?, ?, ?)', (ref, rowid, type_code))
    return inserted

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

  abbrevs = [
      (re.compile('Street'), 'St'),
      (re.compile('Avenue'), 'Ave'),
      (re.compile('Boulevard'), 'Blvd'),
      (re.compile('Freeway'), 'Fwy'),
      (re.compile('Parkway'), 'Pkwy'),
      (re.compile('Lane'), 'Ln'),
      (re.compile('Road'), 'Rd'),
      (re.compile('Square'), 'Sq'),
      (re.compile('North'), 'N'),
      (re.compile('East'), 'E'),
      (re.compile('South'), 'S'),
      (re.compile('West'), 'W'),
      (re.compile('Northeast'), 'NE'),
      (re.compile('Southeast'), 'SE'),
      (re.compile('Southwest'), 'SW'),
      (re.compile('Northwest'), 'NW')
  ]

  def __init__(self):
    self.db = None
    self.cache_path = 'data/osm_cache'

    if not os.path.exists(self.cache_path):
      os.mkdir(self.cache_path)

  def load_name_database(self, cluster):
    cluster_id = cluster.identifier()
    db_path = f'{self.cache_path}/{cluster_id}.db'
    data_cached = os.path.exists(db_path)
    
    if data_cached:
      self.db = OSMDatabase(db_path)
    else:
      logging.info('requesting data from OSM ...')
      query = self.query_for_cluster(cluster)
      res = requests.post(url=self.api_url, data=query)
      res.encoding = 'utf-8'
      name_count = self.create_database(db_path, res.text, 1, [2, 3, 4, 5])
      logging.info('created database with %d unique names.', name_count)

  def query_for_cluster(self, cluster):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name"; false)]; ('
    for bounding_box in cluster.bounding_boxes():
      bbox = ','.join(map(str, bounding_box))
      query += f'node["name"][!"shop"]({bbox}); way["name"]({bbox}); rel["name"]({bbox}); '
    query += '); out qt;'
    return query

  def create_database(self, db_path, csv_text, type_col, name_cols):
    csv_input = io.StringIO(csv_text, newline=None) # universal newlines mode
    reader = csv.reader(csv_input, delimiter='\t')
    self.db = OSMDatabase(db_path)
    self.db.create_tables()
    col_num = len(name_cols) + 2
    name_count = 0
    for row in reader:
      if len(row) != col_num:
        continue
      ref = row[0]
      ref_type = row[type_col]
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        name_count += self.db.insert_ref(name, ref, ref_type)
    self.db.commit_changes()
    return name_count

  def find_names(self, text, anchors):
    text = text + ' '  # also catch matches in last word
    text_len = len(text)
    names = {}
    prev_match_end = 0
    suffixes_for_prefixes = {}

    for start, end in anchors:
      if start < prev_match_end:
        continue

      prefix = text[start:end]
      if prefix in suffixes_for_prefixes:
        suffixes = suffixes_for_prefixes[prefix]
      else:
        suffixes = self.get_suffixes(prefix)
        suffixes_for_prefixes[prefix] = suffixes

      text_pos = end
      longest_match = None
      while text_pos < text_len and len(suffixes) > 0:
        next_char = text[text_pos]
        trimmed_suffixes = []
        for name, suffix in suffixes:
          if suffix == '':
            longest_match = name
          elif suffix[0] == next_char:
            trimmed_suffixes.append((name, suffix[1:]))
        suffixes = trimmed_suffixes
        text_pos += 1

      if longest_match != None:
        prev_match_end = text_pos
        if longest_match not in names:
          names[longest_match] = []
        names[longest_match].append(start)

    matches = []
    for name, positions in names.items():
      refs = self.db.get_refs(name)
      match = OSMMatch(name, positions, refs)
      matches.append(match)

    return matches

  def get_suffixes(self, prefix):
    found_names = self.db.find_names(prefix)
    suffixes = []
    for name in found_names:
      suffix = name[len(prefix):]
      suffixes.append((name, suffix))
      short_version = self.abbreviated(suffix)
      if short_version != suffix:
        suffixes.append((name, short_version))
    return suffixes

  def abbreviated(self, name):
    short_version = name
    for regex, repl in self.abbrevs:
      short_version = regex.sub(repl, short_version)
    return short_version
