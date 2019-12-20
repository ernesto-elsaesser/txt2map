import os
import csv
import json
from geoparser import GeoNamesCache, GeoNamesAPI


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


# data can be loaded from http://download.geonames.org/export/dump/
all_countries_path = '../allCountries.txt'
data_file = open(all_countries_path, encoding='utf-8')
reader = csv.reader(data_file, delimiter='\t')

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
  if pop < 100000:
    continue

  name = row[1]
  if not len(name) > 3:
    continue

  if fcl == 'P':
    pop *= 50

  id = row[0]
  insert(name, id, pop)

  if ' ' in name:
    parts = grams(name)
    alt_names = row[3].split(',')
    for alt_name in alt_names:
      if alt_name in parts and len(alt_name) < len(name):
        insert(alt_name, id, pop)

  if reader.line_num > next_log:
    print('at row', next_log)
    next_log += 500_000


def insert_top_level(geoname):
  # use API directly to get all names
  detailed = GeoNamesAPI.get_geoname(country.id)
  defaults[detailed.name] = country.id
  defaults[detailed.asciiname] = country.id
  for entry in detailed.altnames:
    if 'lang' in entry and entry['lang'] == 'en' and entry['name'] != country.name:
      defaults[entry['name']] = country.id


# make sure we have all top levels and their alt names
continent_map = {}
cache = GeoNamesCache()
continents = cache.get_children(6295630)  # Earth
for continent in continents:
  print('loading countries in', continent.name)
  insert_top_level(continent)
  countries = cache.get_children(continent.id)
  for country in countries:
    continent_map[country.cc] = continent.name
    insert_top_level(country)

# common abbreviations
defaults['U.S'] = 6252001
defaults['US'] = 6252001
defaults['USA'] = 6252001
defaults['EU'] = 6255148
defaults['UAE'] = 290557
defaults['USSR'] = 8354411

# oceans
defaults['Atlantic'] = 3373405
defaults['Atlantic Ocean'] = 3373405
defaults['Pacific'] = 4030875 # 2363254
defaults['Pacific Ocean'] = 4030875 # 2363254
defaults['Indian Ocean'] = 1545739
defaults['Arctic Ocean'] = 2960860
defaults['Southern Ocean'] = 4036776

stop_words = ['West', 'South', 'East', 'North',
              'North-West', 'South-West', 'North-East', 'South-East', 
              'Northwest', 'Southwest', 'Northeast', 'Southeast', 
              'North West', 'South West', 'North East', 'South East', 
              'Western', 'Southern', 'Eastern', 'Northern',
              'West Coast', 'South Coast', 'East Coast', 'North Coast',
              'Ocean', 'Island', 'Delta', 'Bay']

for word in stop_words:
  if word in defaults:
    del defaults[word]

defaults_str = json.dumps(defaults)
defaults_file = 'geoparser/defaults.json'
with open(defaults_file, 'w') as f:
  f.write(defaults_str)

continent_str = json.dumps(continent_map)
continent_file = 'geoparser/continents.json'
with open(continent_file, 'w') as f:
  f.write(continent_str)

print(f'inserted {len(defaults)} entries.')
