import os
import requests
import io
import zipfile
import csv
import sqlite3

url = 'http://download.geonames.org/export/dump/shapes_all_low.zip'
res = requests.get(url=url)
bin_stream = io.BytesIO(res.content)
zipfile = zipfile.ZipFile(bin_stream)
data = zipfile.read('shapes_all_low.txt')
text = data.decode('utf-8')
str_stream = io.StringIO(text)
csv.field_size_limit(1000000)
reader = csv.reader(str_stream, delimiter='\t')
print('shapes loaded from GeoNames.')

db_path = 'geoparser/shapes.db'
if os.path.exists(db_path):
  os.remove(db_path)

db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.execute('CREATE TABLE shapes (geoname_id INT, geojson TEXT)')
cursor.execute('CREATE INDEX id_index ON shapes(geoname_id)')

next(reader)
for row in reader:
  cursor.execute('INSERT INTO shapes VALUES (?, ?)', row)
    
db.commit()
print('shapes stored in SQLite database.')
