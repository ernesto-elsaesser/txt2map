import os
import csv
import json
from .geonames import GeoNamesCache, GeoNamesAPI
from .config import Config


class Gazetteer:

  @staticmethod
  def defaults():
    return Gazetteer._load('defaults')

  @staticmethod
  def demonyms():
    return Gazetteer._load('demonyms')

  @staticmethod
  def continent_map():
    return Gazetteer._load('continent_map')

  @staticmethod
  def country_boxes():
    return Gazetteer._load('country_boxes')

  @staticmethod
  def update_top_level():
    continents = {}
    countries = {}
    continent_map = {}

    cache = GeoNamesCache()
    for continent in cache.get_children(6295630):  # Earth
      continents[continent.name] = continent.id
      print('loading countries in', continent.name)
      for country in cache.get_children(continent.id):
        continent_map[country.cc] = continent.name
        full = GeoNamesAPI.get_geoname(country.id)  # names are not cached
        countries[full.name] = country.id
        countries[full.asciiname] = country.id
        for entry in full.altnames:
          if 'lang' in entry and entry['lang'] == 'en':
            countries[entry['name']] = country.id

    Gazetteer._save('continents', continents)
    Gazetteer._save('countries', countries)
    Gazetteer._save('continent_map', continent_map)

  @staticmethod
  def extract_large_entries(data_path):

    top_names = {}
    top_pops = {}

    data_file = open(data_path, encoding='utf-8')
    reader = csv.reader(data_file, delimiter='\t')

    stop_words = ['West', 'South', 'East', 'North',
                  'North-West', 'South-West', 'North-East', 'South-East',
                  'Northwest', 'Southwest', 'Northeast', 'Southeast',
                  'North West', 'South West', 'North East', 'South East',
                  'Western', 'Southern', 'Eastern', 'Northern',
                  'West Coast', 'South Coast', 'East Coast', 'North Coast',
                  'Central', 'Ocean', 'Island', 'Delta', 'Bay', 'King', 'Union']

    pop_limit = Config.gazetteer_population_limit
    last_log = 0
    for row in reader:
      fcl = row[6]
      if fcl in ['S', 'R']:
        continue

      pop = int(row[14])
      if pop < self.pop_limit:
        continue

      name = row[1]
      if not len(name) > 3:
        continue

      id = int(row[0])
      if (id == 6295630):
        continue # Earth

      names = [name]
      if ' ' in name:
        parts = Gazetteer._grams(name)
        alt_names = row[3].split(',')
        for alt_name in alt_names:
          if alt_name in parts:
            names.append(alt_name)

      fcl = row[6]
      if fcl not in top_pops:
        top_names[fcl] = {}
        top_pops[fcl] = {}

      for name in names:
        if name in stop_words:
          continue
        if name in top_names[fcl] and top_pops[fcl][name] >= pop:
          continue
        top_names[fcl][name] = id
        top_pops[fcl][name] = pop

      if reader.line_num > last_log + 500_000:
        print('at row', reader.line_num)
        last_log = reader.line_num

    for fcl in top_names:
      Gazetteer._save(fcl, top_names[fcl])

  @staticmethod
  def update_defaults():

    defaults = {}
    stopwords = Gazetteer._load('stopwords')

    continents = Gazetteer._load('continents')
    for toponym in continents:
      defaults[toponym] = continents[toponym]

    oceans = Gazetteer._load('oceans')
    for toponym in oceans:
      defaults[toponym] = oceans[toponym]

    countries = Gazetteer._load('countries')
    for toponym in countries:
      defaults[toponym] = countries[toponym]

    class_order = Config.gazetteer_class_prio
    for fcl in class_order:
      entries = Gazetteer._load(fcl)
      for toponym in entries:
        if toponym not in defaults and toponym not in stopwords:
          defaults[toponym] = entries[toponym]

    Gazetteer._save('defaults', defaults)
    print('Gazetteer updated.')

  @staticmethod
  def _load(file_name):
    dirname = os.path.dirname(__file__)
    file_path = f'{dirname}/data/{file_name}.json'
    with open(file_path, 'r') as f:
      data = json.load(f)
    return data

  @staticmethod
  def _save(file_name, obj):
    dirname = os.path.dirname(__file__)
    file_path = f'{dirname}/data/{file_name}.json'
    with open(file_path, 'w') as f:
      json.dump(obj, f)

  @staticmethod
  def _grams(name):
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
    if name in grams:
      grams.remove(name)
    return grams
