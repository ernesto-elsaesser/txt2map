import sys
import os
import requests
import io
import zipfile
import csv
import sqlite3
import geonames

db_path = 'data/geonames.db'
db = sqlite3.connect(db_path)
cursor = db.cursor()

def insert(name, id, lat, lng, fcode, cc, adm1, population):
  cursor.execute('INSERT INTO geonames VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                 (name, id, lat, lng, fcode, cc, adm1, population))

continents = geonames.GeoNamesAPI.get_children(6295630) # Earth
for g in continents:
  insert(g.name, g.id, g.lat, g.lng, g.fcode, g.cc, g.adm1, g.population)

db.commit()
db.close()
