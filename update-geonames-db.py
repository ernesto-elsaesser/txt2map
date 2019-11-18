import os
import requests
import io
import zipfile
import csv
import sqlite3

url = 'http://download.geonames.org/export/dump/cities5000.zip'
res = requests.get(url=url)
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

cursor.execute('CREATE TABLE geonames (name VARCHAR(100) NOT NULL UNIQUE, ids TEXT NOT NULL)')
cursor.execute('CREATE INDEX names_index ON geonames(name)')

for row in reader:
  id = row[0]
  name = row[1]

  cursor.execute('SELECT ids FROM geonames WHERE name = ?', (name, ))
  row = cursor.fetchone()
  if row == None:
    cursor.execute('INSERT INTO geonames VALUES (?, ?)', (name, str(id)))
  else:
    ids = row[0] + ',' + str(id)
    cursor.execute('UPDATE geonames SET ids = ? WHERE name = ?', (ids, name))
    
db.commit()
print('names stored.')
