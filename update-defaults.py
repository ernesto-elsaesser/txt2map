import os
import sqlite3
from geoparser import GeoNamesAPI

db_path = 'geoparser/defaults.db'
if os.path.exists(db_path):
  os.remove(db_path)

db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.execute('CREATE TABLE defaults (name TEXT UNIQUE, geoname_id INT)')


def insert(name, geoname_id):
  try:
    cursor.execute('INSERT INTO defaults VALUES (?, ?)', (name, geoname_id))
  except:
    pass

def insert_names(geoname):
  print(geoname.name)
  detailed = GeoNamesAPI.get_geoname(geoname.id)
  insert(detailed.name, geoname.id)
  insert(detailed.asciiname, geoname.id)
  if detailed.cc != '-':
    insert(detailed.cc, geoname.id)
  for entry in detailed.altnames:
    if ('lang' not in entry or entry['lang'] == 'en') and entry['name'] != geoname.name:
      insert(entry['name'], geoname.id)


continents = GeoNamesAPI.get_children(6295630) # Earth
for continent in continents:
  insert_names(continent)
  countries = GeoNamesAPI.get_children(continent.id)
  for country in countries:
    insert_names(country)

insert('U.S.', 6252001)

# TODO: get capitals?

db.commit()
db.close()
