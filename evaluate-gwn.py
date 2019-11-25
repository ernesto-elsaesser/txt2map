import os
import logging
import csv
import json
import evaluator

# Evaluate the txt2map geoparser on the GeoWebNews corpus
# - only 'Literal' annotations are used for evaluation
# - for multiple OSM elements, the average coordinate is used

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%H:%M:%S")

corpus_dir = 'corpora/GeoWebNews/'

evl = evaluator.CorpusEvaluator(1) # Accuracy@1km
evl.start_corpus('GeoWebNews')

count = 1
limit = 4

for path in os.listdir(corpus_dir):
  if not path.endswith('.txt'):
    continue

  if count > limit: break
  count += 1

  text_path = corpus_dir + path
  annotation_path = corpus_dir + path.replace('txt', 'ann')

  with open(text_path, encoding='utf-8') as f:
    text = f.read()

  evl.start_document(path, text)

  pos_for_tag = {}
  gold_annotations = []

  with open(annotation_path, encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')

    for row in reader:
      id = row[0]
      data = row[1].split(' ')

      if id.startswith('T'):  # BRAT token
        annotation_type = data[0]
        position = data[1]
        if annotation_type == 'Literal':
          pos_for_tag[id] = int(position)
          
      elif id.startswith('#'):  # BRAT annotator note
        tag_id = data[1]
        if tag_id not in pos_for_tag:
            continue
        pos = pos_for_tag[tag_id]
        if ',' in row[2]:
          coords = row[2].split(',')
          lat = float(coords[0].strip())
          lng = float(coords[1].strip())
          evl.test_gold_coordinate(pos, lat, lng)
        else:
          geoname_id = int(row[2])
          evl.test_gold_geoname(pos, geoname_id)

  evl.finish_document()

evl.finish_corpus()
