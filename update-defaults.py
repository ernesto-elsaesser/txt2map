import os
import csv
import json

# data can be loaded from http://download.geonames.org/export/dump/
all_countries_path = '../allCountries.txt'
data_file = open(all_countries_path, encoding='utf-8')
reader = csv.reader(data_file, delimiter='\t')

defaults = {}
top_pops = {}

def insert(name, id, pop):
  global defaults, top_pops
  if name in defaults:
    top_pop = top_pops[name]
    if pop < top_pop:
      return
  defaults[name] = id
  top_pops[name] = pop

def grams(name):
  parts = name.split(' ')
  grams = []
  l = len(parts)
  for i in range(l):
    p = parts[i]
    if not len(p) < 3:
      grams.append(p)
    if i < l-1:
      p += ' ' + parts[i+1]
      grams.append(p)
      if i < l-2:
        p += ' ' + parts[i+2]
        grams.append(p)
  return grams

next_log = 500_000
for row in reader:
  fcl = row[6]
  if fcl not in ['A', 'H', 'L', 'P']:
    continue

  pop = int(row[14])
  if pop < 50000:
    continue

  name = row[1]
  if not len(name) > 3:
    continue

  if ' ' in name:
    parts = grams(name)
    alt_names = row[3].split(',')
    for alt_name in alt_names:
      if alt_name in parts and len(alt_name) < len(name):
        name = alt_name
        if ' ' not in name:
          break

  id = row[0]
  insert(name, id, pop)

  if reader.line_num > next_log:
    print('at row', next_log)
    next_log += 500_000

stop_words = ['North','South','East','West']
for word in stop_words:
  if word in defaults:
    del defaults[word]

defaults_str = json.dumps(defaults)
defaults_file = 'geoparser/defaults.json'
with open(defaults_file, 'w') as f:
  f.write(defaults_str)

print(f'inserted {len(defaults)} entries.')
