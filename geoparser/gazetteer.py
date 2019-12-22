import os
import csv
import json
from .geonames import GeoNamesCache, GeoNamesAPI
from .geo import GeoUtil


class Gazetteer:

  pop_limit = 100_000

  def __init__(self, gns_cache):
    self.dirname = os.path.dirname(__file__)
    self.cache = gns_cache
    self.defaults = self._load('defaults')
    self.continents = self._load('continents')
    self.continent_map = self._load('continent_map')

  def update_top_level(self):
    continents = {}
    countries = {}
    continent_map = {}

    for continent in self.cache.get_children(6295630):  # Earth
      continents[continent.name] = continent.id
      print('loading countries in', continent.name)
      for country in self.cache.get_children(continent.id):
        continent_map[country.cc] = continent.name
        full = GeoNamesAPI.get_geoname(country.id)  # names are not cached
        countries[full.name] = country.id
        countries[full.asciiname] = country.id
        for entry in full.altnames:
          if 'lang' in entry and entry['lang'] == 'en':
            countries[entry['name']] = country.id

    self._save('continents', continents)
    self._save('countries', countries)
    self._save('continent_map', continent_map)

    self.continents = continents
    self.continent_map = continent_map

  def extract_large_entries(self, data_path):

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
                  'Ocean', 'Island', 'Delta', 'Bay']

    last_log = 0
    for row in reader:
      fcl = row[6]
      if fcl in ['S', 'R']:
        continue

      pop = int(row[14])
      if pop < Gazetteer.pop_limit:
        continue

      name = row[1]
      if not len(name) > 3:
        continue

      names = [name]
      if ' ' in name:
        parts = self._grams(name)
        alt_names = row[3].split(',')
        for alt_name in alt_names:
          if alt_name in parts:
            names.append(alt_name)

      id = int(row[0])
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
      self._save(fcl, top_names[fcl])

  def update_defaults(self, class_order=['P', 'A', 'L', 'T']):

    defaults = {}

    demonyms = self._load('demonyms')

    continents = self._load('continents')
    for toponym in continents:
      defaults[toponym] = continents[toponym]
      for demonym in demonyms[toponym]:
        defaults[demonym] = continents[toponym]

    oceans = self._load('oceans')
    for toponym in oceans:
      defaults[toponym] = oceans[toponym]

    countries = self._load('countries')
    for toponym in countries:
      defaults[toponym] = countries[toponym]
      if toponym in demonyms:
        for demonym in demonyms[toponym]:
          defaults[demonym] = countries[toponym]

    for fcl in class_order:
      entries = self._load(fcl)
      for toponym in entries:
        if toponym not in defaults:
          defaults[toponym] = entries[toponym]

    # common abbreviations
    countries['U.S.'] = 6252001
    countries['US'] = 6252001
    countries['USA'] = 6252001
    countries['EU'] = 6255148
    countries['UAE'] = 290557
    countries['D.C.'] = 4140963

    self._save('defaults', defaults)
    self.defaults = defaults

  def continent_name(self, geoname):

    if geoname.is_continent:
      return geoname.name

    if geoname.cc != "-":
      return self.continent_map[geoname.cc]

    min_dist = float('inf')
    closest_name = None
    for geoname_id in self.continents.values():
      c = self.cache.get(geoname_id)
      dist = GeoUtil.distance(geoname.lat, geoname.lon, c.lat, c.lon)
      if dist < min_dist:
        min_dist = dist
        closest_name = c.name
    return closest_name
    
  def _load(self, file_name):
    file_path = f'{self.dirname}/data/{file_name}.json'
    with open(file_path, 'r') as f:
      data = json.load(f)
    return data

  def _save(self, file_name, obj):
    file_path = f'{self.dirname}/data/{file_name}.json'
    with open(file_path, 'w') as f:
      json.dump(obj, f)

  def _grams(self, name):
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
