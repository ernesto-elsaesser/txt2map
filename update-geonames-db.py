import os
import requests
import io
import zipfile
import csv
import geonames

url = 'http://download.geonames.org/export/dump/cities5000.zip'
res = requests.get(url=url)
bin_stream = io.BytesIO(res.content)
zipfile = zipfile.ZipFile(bin_stream)
data = zipfile.read('cities5000.txt')
text = data.decode('utf-8')
str_stream = io.StringIO(text)
reader = csv.reader(str_stream, delimiter='\t')
print('names loaded.')

if os.path.exists('data/geonames.db'):
  os.remove('data/geonames.db')

db = geonames.GeoNamesDatabase()
db.create_tables()

for row in reader:

  id = row[0]

  names = set()
  official_name = row[1]
  names.add(row[1])
  names.add(row[2])
  alternative_names = row[3].split(',')
  for name in alternative_names:
    if name[:3] == official_name[:3]:
      names.add(name)

  for name in names:
    db.insert_geoname(name, id)
    
db.commit_changes()
print('names stored.')
