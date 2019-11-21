import os
import csv
import json
import geonames

# adapted from https://github.com/milangritta/Pragmatic-Guide-to-Geoparsing-Evaluation/blob/master/dataset.py

orig_dir = 'corpora/GeoWebNews/'
dest_dir = 'eval/GeoWebNews/'

if not os.path.exists(dest_dir):
  os.mkdir(dest_dir)

geo_client = geonames.GeoNamesClient()
count = 1
limit = 5

for path in os.listdir(orig_dir):
  if not path.endswith(".ann"):
    continue

  if count > limit: exit()
  count += 1

  orig_path = orig_dir + path
  dest_path = dest_dir + path.replace('ann', 'json')
  print(orig_path, '>', dest_path)

  annotations = {}
  with open(orig_path, encoding="utf-8") as orig:
    reader = csv.reader(orig, delimiter='\t')
    for row in reader:
      id = row[0]
      data = row[1].split(" ")
      if id.startswith("T"): # token
        if data[0] != "Literal":
          continue

        annotations[id] = {'text': row[2],
                    'pos': int(data[1])}
          
      if id.startswith("#"):  # annotator note
        tag_id = data[1]
        if tag_id not in annotations:
            continue

        if ',' in row[2]:
          coords = row[2].split(",")
          annotations[tag_id]['lat'] = float(coords[0].strip())
          annotations[tag_id]['lng'] = float(coords[1].strip())
        else:
          geoname = geo_client.get_geoname(row[2])
          annotations[tag_id]['lat'] = geoname.lat
          annotations[tag_id]['lng'] = geoname.lng

    json_list = []
    keys = list(annotations.keys())
    for key in keys:
      if 'lat' in annotations[key]:
        json_list.append(annotations[key])
    json_str = json.dumps(json_list)

    with open(dest_path, mode='w', encoding="utf-8") as dest:
      dest.write(json_str)
