import os
import csv
import json
from .geonames import GeoNamesAPI
from .datastore import Datastore


class Gazetteer:

  common_abbrevs = {'U.S.': 6252001,
                    'US': 6252001,
                    'USA': 6252001,
                    'America': 6252001,
                    'UK': 2635167,
                    'Britain': 2635167,
                    'EU': 6255148,
                    'UAE': 290557,
                    'D.C.': 4140963}

  @staticmethod
  def top_level():
    countries = Gazetteer.countries()

    top_level = {}
    top_level.update(Gazetteer.us_states())

    # default senses are the cities, not the states
    del top_level['New York'] 
    del top_level['Washington']

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
  def large_entries(pop_limit=50_000):
    return Datastore.load_gazetteer(str(pop_limit))

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

    for continent in Datastore.get_children(6295630):  # Earth
      continents[continent.name] = continent.id
      print('loading countries in', continent.name)
      for country in Datastore.get_children(continent.id):
        continent_map[country.cc] = continent.name
        countries[country.name] = country.id
        if country.id == 6252001:  # US
          for us_state in Datastore.get_children(country.id):
            us_states[us_state.name] = us_state.id
        if country.id == 2635167:  # UK
          for uk_country in Datastore.get_children(country.id):
            continent_map[uk_country.cc] = continent.name
            countries[uk_country.name] = uk_country.id

    Datastore.save_gazetteer('continents', continents)
    Datastore.save_gazetteer('countries', countries)
    Datastore.save_gazetteer('us_states', us_states)
    Datastore.save_gazetteer('continent_map', continent_map)

  @staticmethod
  def extract_large_entries(data_path, pop_limit=50_000):

    toponyms = set()

    last_log = 0

    data_file = open(data_path, encoding='utf-8')
    reader = csv.reader(data_file, delimiter='\t')
    for row in reader:
      pop = int(row[14])
      if pop < pop_limit:
        continue

      toponyms.add(row[1])
      toponyms.add(row[2]) # ascii name

      if reader.line_num > last_log + 500_000:
        print('at row', reader.line_num)
        last_log = reader.line_num

    Datastore.save_gazetteer(str(pop_limit), list(toponyms))

    print('Cities extracted.')


