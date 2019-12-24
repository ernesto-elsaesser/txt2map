import os
import csv
import json
from .geonames import GeoNamesCache, GeoNamesAPI
from .config import Config


class Gazetteer:

  def __init__(self):
    dirname = os.path.dirname(__file__)
    self.data_dir = dirname + '/data'

    self.defaults = self._load('defaults')
    self.continents = self._load('continents')
    self.continent_map = self._load('continent_map')
    self.country_boxes = self._load('country_boxes')

    self.lookup_tree = {}
    for toponym in self.defaults:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

  def lookup_prefix(self, prefix):
    key = prefix[:2]
    if key not in self.lookup_tree:
      return []
    toponyms = self.lookup_tree[key]
    return [t for t in toponyms if t.startswith(prefix)]

  def continent_name(self, geoname):

    if geoname.is_continent:
      return geoname.name

    if geoname.cc in self.continent_map:
      return self.continent_map[geoname.cc]

    lat = geoname.lat
    lon = geoname.lon
    for name, box in self.country_boxes.items():
      if box[1] < lat < box[3] and box[0] < lon < box[2]:  # [w, s, e, n]
        return self.continent_map[name]
    return 'Nowhere'

  def update_top_level(self):
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

  def update_defaults(self):

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

    class_order = Config.gazetteer_class_prio
    for fcl in class_order:
      entries = self._load(fcl)
      for toponym in entries:
        if toponym not in defaults:
          defaults[toponym] = entries[toponym]
          if toponym in demonyms:
            for demonym in demonyms[toponym]:
              defaults[demonym] = entries[toponym]

    # common abbreviations
    defaults['U.S.'] = 6252001
    defaults['US'] = 6252001
    defaults['USA'] = 6252001
    defaults['EU'] = 6255148
    defaults['UAE'] = 290557
    defaults['D.C.'] = 4140963

    self._save('defaults', defaults)
    self.defaults = defaults
    
  def _load(self, file_name):
    file_path = f'{self.data_dir}/{file_name}.json'
    with open(file_path, 'r') as f:
      data = json.load(f)
    return data

  def _save(self, file_name, obj):
    file_path = f'{self.data_dir}/{file_name}.json'
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
