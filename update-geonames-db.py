import os
import requests
import io
import zipfile
import csv
import sqlite3

cities_url = 'http://download.geonames.org/export/dump/cities5000.zip'
res = requests.get(url=cities_url)
bin_stream = io.BytesIO(res.content)
zipfile = zipfile.ZipFile(bin_stream)
data = zipfile.read('cities5000.txt')
text = data.decode('utf-8')
str_stream = io.StringIO(text)
reader = csv.reader(str_stream, delimiter='\t')
print('names loaded.')

db_path = 'data/geonames.db'
if os.path.exists(db_path):
  os.remove(db_path)

db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.execute('''CREATE TABLE geonames (
    name VARCHAR(100), 
    id INT, 
    cc CHAR(2), 
    adm1 VARCHAR(20),
    lat REAL, 
    lng REAL, 
    population INT)''')
cursor.execute('CREATE INDEX names_index ON geonames(name)')

for row in reader:
  population = int(row[14])
  if population < 10000:
    continue

  id = int(row[0])
  name = row[1]
  lat = float(row[4])
  lng = float(row[5])
  cc = row[8]
  adm1 = row[10]

  cursor.execute(
      'INSERT INTO geonames VALUES (?, ?, ?, ?, ?, ?, ?)',
       (name, id, cc, adm1, lat, lng, population))
    
db.commit()
print('names stored.')

