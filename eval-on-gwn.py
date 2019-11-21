import os
import csv
import json
import geonames
import parser

corpus_dir = 'corpora/GeoWebNews/'
result_dir = 'eval/GeoWebNews/'

parser = parser.Geoparser()
geonames_client = geonames.GeoNamesClient()
count = 1
limit = 1

for path in os.listdir(corpus_dir):
  if not path.endswith(".txt"):
    continue

  if count > limit: exit()
  count += 1

  text_path = corpus_dir + path
  annotation_path = corpus_dir + path.replace('txt', 'ann')
  print('testing', path)

  with open(text_path, encoding="utf-8") as f:
    text = f.read()

  # produce gold data
  annotations = {}
  with open(annotation_path, encoding="utf-8") as f:
    reader = csv.reader(f, delimiter='\t')

    for row in reader:
      id = row[0]
      if id.startswith("T"):  # BRAT token
        data = row[1].split(" ")
        if data[0] == "Literal":
          annotations[id] = {'text': row[2], 'pos': int(data[1])}
          
      elif id.startswith("#"):  # BRAT annotator note
        tag_id = data[1]
        if tag_id not in annotations:
            continue

        if ',' in row[2]: # non-GeoNames coordinate
          coords = row[2].split(",")
          annotations[tag_id]['lat'] = float(coords[0].strip())
          annotations[tag_id]['lng'] = float(coords[1].strip())
        else: # GeoName ID
          geoname = geonames_client.get_geoname(row[2])
          annotations[tag_id]['lat'] = geoname.lat
          annotations[tag_id]['lng'] = geoname.lng

    gold_labels = list(annotations.values())

    # run txt2map
    clusters = parser.parse(text)

    # evaluate results: correct if name + coord in txt2map GeoNames or OSM matches

    # TODO!