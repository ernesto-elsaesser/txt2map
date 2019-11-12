import sys
import os
import csv
import geonames

geonames_csv_path = sys.argv[1]

if os.path.exists('data/geonames.db'):
  os.remove('data/geonames.db')

db = geonames.GeoNamesDatabase()
db.create_tables()

with open(geonames_csv_path, 'r') as f:
  reader = csv.reader(f, delimiter='\t')
  row_num = 0
  for row in reader:
    row_num += 1
    if row_num % 1000000 == 0:
      print(f'processed {int(row_num / 1000000)}m rows')

    feature_class = row[6]
    if feature_class != 'A' and feature_class != 'P':
      continue

    population = int(row[14])
    if population < 50000:
      continue

    id = row[0]
    lat = row[4]
    lon = row[5]
    feature_code = row[7]
    country_code = row[8]

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

print('done.')
