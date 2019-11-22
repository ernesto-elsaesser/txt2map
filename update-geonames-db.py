import sys
import os
import requests
import io
import zipfile
import csv
import sqlite3
import geonames

# provide path to allCountries.txt as parameter
# data can be loaded from http://download.geonames.org/export/dump/
all_countries_path = '../allCountries.txt' # sys.argv[1]
data_file = open(all_countries_path, encoding='utf-8')

db_path = 'data/geonames.db'
if os.path.exists(db_path):
  os.remove(db_path)

db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.execute('''CREATE TABLE geonames (
    name VARCHAR(100), 
    id INT, 
    lat REAL, 
    lng REAL,
    fcode VARCHAR(10),
    cc CHAR(2),
    adm1 VARCHAR(20),
    population INT)''')
cursor.execute('CREATE INDEX name_index ON geonames(name)')

def insert(name, id, lat, lng, fcode, cc, adm1, population):
  cursor.execute('INSERT INTO geonames VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                 (name, id, lat, lng, fcode, cc, adm1, population))

reader = csv.reader(data_file, delimiter='\t')
count = 0
next_log = 500_000
for row in reader:
  fclass = row[6]
  if fclass not in ['L', 'A', 'P']:
    continue
  population = int(row[14])
  if population < 10000:
    continue
  id = int(row[0])
  name = row[1]
  alt_names = row[3].split(',')
  lat = float(row[4])
  lng = float(row[5])
  fcode = row[7]
  cc = row[8]
  adm1 = row[10]
  insert(name, id, lat, lng, fcode, cc, adm1, population)
  for alt_name in alt_names:
    if alt_name in name:
      insert(alt_name, id, lat, lng, fcode, cc, adm1, population)

  count += 1
  if reader.line_num > next_log:
    print('at row', next_log)
    next_log += 500_000

db.commit()
db.close()

print('inserted', count, 'entries.')
