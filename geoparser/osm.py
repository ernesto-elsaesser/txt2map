import requests
import sqlite3
import csv
import logging
import os
import re
import io

class OSMElement:

  def __init__(self, reference, element_type):
    self.reference = reference
    self.element_type = element_type

  def __repr__(self):
    return f'{self.element_type}/{self.reference}'

  def url(self):
    return 'https://www.openstreetmap.org/' + str(self)

class OSMMatch:

  def __init__(self, name, positions, elements):
    self.name = name
    self.positions = positions
    self.elements = elements

class OSMDatabase:

  type_names = ['node', 'way', 'relation']

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

  def insert_element(self, name, element):
    if len(name) < 2:
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
    type_code = self.type_names.index(element.element_type)
    self.cursor.execute('INSERT INTO osm VALUES(?, ?, ?)', 
                        (element.reference, rowid, type_code))
    return inserted

  def get_elements(self, name):
    rowid = self.get_rowid(name)
    self.cursor.execute(
        'SELECT ref,type_code FROM osm WHERE names_rowid = ?', (rowid, ))
    elements = []
    for row in self.cursor.fetchall():
      element_type = self.type_names[row[1]]
      element = OSMElement(row[0], element_type)
      elements.append(element)
    return elements



class OSMMatcher:

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
    self.cache_path = 'osmcache'

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
      boxes = cluster.bounding_boxes()
      csv_reader = OverpassAPI.load_names_in_bounding_boxes(boxes)
      name_count = self.create_database(db_path, csv_reader, 1, [2, 3, 4, 5])
      logging.info('created database with %d unique names.', name_count)

  def create_database(self, db_path, csv_reader, type_col, name_cols):
    self.db = OSMDatabase(db_path)
    self.db.create_tables()
    col_num = len(name_cols) + 2
    name_count = 0
    for row in csv_reader:
      if len(row) != col_num:
        continue
      element = OSMElement(row[0], row[type_col])
      names = set(map(lambda c: row[c], name_cols))
      for name in names:
        name_count += self.db.insert_element(name, element)
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
      elements = self.db.get_elements(name)
      match = OSMMatch(name, positions, elements)
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

class OverpassAPI:

  @staticmethod
  def load_all_coordinates(elements):
    query = '[out:csv(::lat, ::lon; false)]; ('
    for elem in elements:
      query += f'{elem.element_type}({elem.reference}); '
    query += '); >>; node._; out;'
    return OverpassAPI.load_csv(query)

  @staticmethod
  def load_names_in_bounding_boxes(bounding_boxes):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name"; false)]; ('
    for bounding_box in bounding_boxes:
      bbox = ','.join(map(str, bounding_box))
      query += f'node["name"][!"shop"]({bbox}); way["name"]({bbox}); rel["name"]({bbox}); '
    query += '); out qt;'
    return OverpassAPI.load_csv(query)

  @staticmethod
  def load_csv(query):
    url = 'http://overpass-api.de/api/interpreter'
    res = requests.post(url=url, data=query)
    res.encoding = 'utf-8'
    csv_input = io.StringIO(res.text, newline=None)  # universal newlines mode
    reader = csv.reader(csv_input, delimiter='\t')
    return reader
