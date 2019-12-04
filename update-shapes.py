import os
import requests
import io
import zipfile
import csv
import sqlite3
import json

url = 'https://gist.githubusercontent.com/hrbrmstr/91ea5cc9474286c72838/raw/59421ff9b268ff0929b051ddafafbeb94a4c1910/continents.json'
res = requests.get(url=url)
continents = res.json()
print('continents loaded from GitHub.')

url = 'http://download.geonames.org/export/dump/shapes_all_low.zip'
res = requests.get(url=url)
bin_stream = io.BytesIO(res.content)
zipfile = zipfile.ZipFile(bin_stream)
data = zipfile.read('shapes_all_low.txt')
text = data.decode('utf-8')
str_stream = io.StringIO(text)
csv.field_size_limit(1000000)
reader = csv.reader(str_stream, delimiter='\t')
print('countires loaded from GeoNames.')

db_path = 'evaluation/shapes.db'
if os.path.exists(db_path):
  os.remove(db_path)

db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.execute('CREATE TABLE shapes (geoname_id INT, geojson TEXT)')

def insert_continent(id, name):
  for feature in continents['features']:
    if feature['properties']['CONTINENT'] == name:
      geojson = json.dumps(feature['geometry'])
      cursor.execute('INSERT INTO shapes VALUES (?, ?)', (id, geojson))
      return

insert_continent(6255146, 'Africa')
insert_continent(6255147, 'Asia')
insert_continent(6255148, 'Europe')
insert_continent(6255149, 'North America')
insert_continent(6255150, 'South America')
insert_continent(6255151, 'Oceania')
insert_continent(6255152, 'Antarctica')

next(reader)
for row in reader:
  cursor.execute('INSERT INTO shapes VALUES (?, ?)', row)

db.commit()
print('shapes stored in SQLite database.')
