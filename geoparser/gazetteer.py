import os
import csv
import json
from .geonames import GeoNamesAPI
from .datastore import Datastore


class Gazetteer:

  population_limit = 100_000

  common_abbrevs = {'U.S.': 6252001,
                    'US': 6252001,
                    'USA': 6252001,
                    'America': 6252001,
                    'EU': 6255148,
                    'UAE': 290557,
                    'D.C.': 4140963}

  @staticmethod
  def top_level():
    countries = Gazetteer.countries()

    top_level = {}
    top_level.update(countries)

    for toponym, demonyms in Gazetteer.demonyms().items():
      if toponym not in countries:
        continue
      for demonym in demonyms:
        top_level[demonym] = countries[toponym]

    top_level.update(Gazetteer.oceans())
    top_level.update(Gazetteer.continents())
    top_level.update(Gazetteer.common_abbrevs)

    return top_level

  @staticmethod
  def demonyms():
    return Datastore.load_gazetteer('demonyms')

  @staticmethod
  def continents():
    return Datastore.load_gazetteer('continents')

  @staticmethod
  def countries():
    return Datastore.load_gazetteer('countries')

  @staticmethod
  def us_states():
    return Datastore.load_gazetteer('us_states')

  @staticmethod
  def oceans():
    return Datastore.load_gazetteer('oceans')

  @staticmethod
  def admins():
    return Datastore.load_gazetteer('A')

  @staticmethod
  def cities():
    return Datastore.load_gazetteer('P')

  @staticmethod
  def stopwords():
    return Datastore.load_gazetteer('stopwords')

  @staticmethod
  def continent_map():
    return Datastore.load_gazetteer('continent_map')

  @staticmethod
  def country_boxes():
    return Datastore.load_gazetteer('country_boxes')

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

    Datastore.save_gazetteer('continents', continents)
    Datastore.save_gazetteer('countries', countries)
    Datastore.save_gazetteer('continent_map', continent_map)

  @staticmethod
  def extract_large_entries(data_path, classes):

    pop_limit = Gazetteer.population_limit
    toponyms = {}

    for fcl in classes:
      toponyms[fcl] = set()

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

      toponyms[fcl].add(row[1])

      if reader.line_num > last_log + 500_000:
        print('at row', reader.line_num)
        last_log = reader.line_num

    for fcl, names in toponyms.items():
      Datastore.save_gazetteer(fcl, list(names))

    print('Entries extracted.')


