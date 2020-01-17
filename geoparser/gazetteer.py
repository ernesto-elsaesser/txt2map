import os
import csv
import json
from .geonames import GeoNamesCache, GeoNamesAPI
from .config import Config


class Gazetteer:

  @staticmethod
  def demonyms():
    return Gazetteer._load('demonyms')

  @staticmethod
  def continents():
    return Gazetteer._load('continents')

  @staticmethod
  def countries():
    return Gazetteer._load('countries')

  @staticmethod
  def us_states():
    return Gazetteer._load('us_states')

  @staticmethod
  def oceans():
    return Gazetteer._load('oceans')

  @staticmethod
  def admins():
    return Gazetteer._load('A')

  @staticmethod
  def cities():
    return Gazetteer._load('P')

  @staticmethod
  def stopwords():
    return Gazetteer._load('stopwords')

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
    us_states = {}
    continent_map = {}

    cache = GeoNamesCache()
    for continent in cache.get_children(6295630):  # Earth
      continents[continent.name] = continent.id
      print('loading countries in', continent.name)
      for country in cache.get_children(continent.id):
        continent_map[country.cc] = continent.name
        countries[country.name] = country.id
        if country.id == 6252001:  # US
          for state in cache.get_children(country.id):
            us_states[state.name] = state.id

    Gazetteer._save('continents', continents)
    Gazetteer._save('countries', countries)
    Gazetteer._save('us_states', us_states)
    Gazetteer._save('continent_map', continent_map)

  @staticmethod
  def extract_large_entries(data_path, classes):

    pop_limit = Config.gazetteer_population_limit
    top_names = {}
    top_pops = {}

    for fcl in classes:
      top_names[fcl] = {}
      top_pops[fcl] = {}

    last_log = 0

    data_file = open(data_path, encoding='utf-8')
    reader = csv.reader(data_file, delimiter='\t')
    for row in reader:
      fcl = row[6]
      if fcl not in classes:
        continue

      pop = int(row[14])
      if pop < pop_limit:
        continue

      id = int(row[0])
      if (id == 6295630):
        continue # Earth

      name = row[1]
      if name in top_names[fcl] and top_pops[fcl][name] >= pop:
        continue

      top_names[fcl][name] = id
      top_pops[fcl][name] = pop

      if reader.line_num > last_log + 500_000:
        print('at row', reader.line_num)
        last_log = reader.line_num

    for fcl in top_names:
      Gazetteer._save(fcl, top_names[fcl])

    print('Entries extracted.')

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

