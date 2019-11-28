import os
import logging
import requests
import sqlite3
import json

class GeoName:

  def __init__(self, json):
    self.id = json['geonameId']
    self.name = json['name']
    self.population = json['population']
    self.fclass = json['fcl']
    self.fcode = json['fcode']
    self.lat = float(json['lat'])
    self.lng = float(json['lng'])
    self.cc = '-' if 'countryCode' not in json else json['countryCode']
    self.adm1 = '-' if 'adminCode1' not in json else json['adminCode1']

    self.is_city = self.fcode.startswith('PP')

  def __repr__(self):
    return f'{self.name}, {self.cc} [{self.fcode}]'

  def geojson_coordinates(self):
    return [self.lng, self.lat]

  def bounding_box(self, d):
    return [self.lat - d, self.lng - d,
            self.lat + d, self.lng + d]

class Toponym:

  def __init__(self, name, positions):
    self.name = name
    self.positions = positions
    self.candidates = []
    self.selected = None

  def __repr__(self):
    return self.name

class GeoNameCandidate:

  def __init__(self, geoname, hierarchy, mentions):
    self.geoname = geoname
    self.hierarchy = hierarchy
    self.mentions = mentions

  def population(self):
    return self.geoname.population

  def __repr__(self):
    return self.geoname.__repr__()

class ToponymCluster:

  def __init__(self, toponyms, cities, anchor):
    self.toponyms = toponyms
    self.cities = cities
    self.anchor = anchor
    self.city_geonames = [t.selected.geoname for t in cities]
    self.path = [g.name for g in anchor.selected.hierarchy]
    self.size = len(toponyms)
    self.mentions = max(map(lambda t: t.selected.mentions, toponyms))
    self.local_matches = []
    self.confidence = 0

  def identifier(self):
    sorted_ids = sorted(str(g.id) for g in self.city_geonames)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(g.population for g in self.city_geonames)

  def bounding_boxes(self, d=0.1):
    return [g.bounding_box(d) for g in self.city_geonames]

  def __repr__(self):
    path_str = ' > '.join(self.path[1:-1]) # skip Earth
    sorted_geonames = sorted(self.city_geonames, key=lambda g: g.population, reverse=True)
    cities_str = ' + '.join(g.name for g in sorted_geonames)
    return path_str + ' > ' + cities_str

class GeoNamesMatcher:

  def generate_clusters(self, toponyms):
    logging.info('requesting data from GeoNames ...')
    self.get_candidates(toponyms)
    logging.info('disambiguating results ...')
    self.select_candidates(toponyms)
    resolved_toponyms = [t for t in toponyms if t.selected != None]
    return self.cluster_toponyms(resolved_toponyms)

  def get_candidates(self, toponyms):
    toponym_names = [t.name for t in toponyms]
    for toponym in toponyms:
      geonames = GeoNamesAPI.search(toponym.name)
      geonames = [g for g in geonames if g.name == toponym.name]
      for geoname in geonames:
        hierarchy = GeoNamesAPI.get_hierarchy(geoname.id)
        hierarchy_names = set([g.name for g in hierarchy])
        mentions = self.count_mentions(hierarchy_names, toponym_names)
        candidate = GeoNameCandidate(geoname, hierarchy, mentions)
        toponym.candidates.append(candidate)

  def count_mentions(self, hierarchy_names, toponym_names):
    matched_names = set()
    for h_name in hierarchy_names:
      for t_name in toponym_names: 
        if t_name in h_name or h_name in t_name:
          matched_names.add(t_name)
    return len(matched_names)

  def select_candidates(self, toponyms):
    for toponym in toponyms:
      candidates = sorted(toponym.candidates, key=lambda c: c.population(), reverse=True)
      if len(candidates) == 0:
        continue
      best = candidates[0]
      city_candidates = [c for c in candidates if c.geoname.is_city]
      max_mentions = max(map(lambda c: c.mentions, candidates))
      if not best.geoname.is_city:
        for c in city_candidates:
          hierarchy_ids = [g.id for g in c.hierarchy]
          if best.geoname.id in hierarchy_ids:
            best = c
            break
      elif best.mentions < max_mentions:
        for c in city_candidates:
          if c.mentions == max_mentions:
            best = c
            break
      toponym.selected = best

  def cluster_toponyms(self, toponyms):
    seeds = list(sorted(toponyms, key=lambda t: t.selected.population(), reverse=True))

    clusters = []
    bound_names = set()

    while len(seeds) > 0:
      seed = seeds.pop()
      bound_names.add(seed.name)

      # find all matches in the same ADM1 area
      connected = [seed]
      hierarchy_ids = [g.id for g in seed.selected.hierarchy]
      g1 = seed.selected.geoname
      for toponym in toponyms:
        if toponym.name in bound_names:
          continue
        g2 = toponym.selected.geoname
        if g1.cc == g2.cc != '-' and g1.adm1 == g2.adm1 != '-':
          connected.append(toponym)
          bound_names.add(toponym.name)
          seeds.remove(toponym)
        elif g2.id in hierarchy_ids:
          connected.append(toponym)
          if toponym in seeds:
            seeds.remove(toponym)

      cities = [t for t in connected if t.selected.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda c: c.selected.population())
      else:
        anchor = min(connected, key=lambda c: c.selected.population())

      cluster = ToponymCluster(connected, cities, anchor)
      clusters.append(cluster)

    return sorted(clusters, key=lambda c: c.mentions, reverse=True)


class GeoNamesAPI:

  @staticmethod
  def search(name, maxRows=10):
    params = [('name_equals', name), ('maxRows', maxRows)]
    json_dict = GeoNamesAPI.get_json('search', params)
    geonames = []
    if 'geonames' in json_dict:
      json_array = json_dict['geonames']
      geonames = list(map(lambda d: GeoName(json=d), json_array))
    return geonames

  @staticmethod
  def get_hierarchy(id):
    params = [('geonameId', id)]
    json_dict = GeoNamesAPI.get_json('hierarchy', params)
    geonames = []
    if 'geonames' in json_dict:
      json_array = json_dict['geonames']
      geonames = list(map(lambda d: GeoName(json=d), json_array))
    return geonames

  @staticmethod
  def get_geoname(id):
    params = [('geonameId', id)]
    json_dict = GeoNamesAPI.get_json('get', params)
    return GeoName(json=json_dict)

  @staticmethod
  def get_json(endpoint, params):
    url = f'http://api.geonames.org/{endpoint}JSON?username=map2txt'
    for key, value in params:
      url += f'&{key}={value}'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return res.json()

  @staticmethod
  def get_shape(id):
    dirname = os.path.dirname(__file__)
    db = sqlite3.connect(dirname + '/shapes.db')
    cursor = db.cursor()
    cursor.execute('SELECT geojson FROM shapes WHERE geoname_id = ?', (id, ))
    row = cursor.fetchone()
    db.close()
    if row == None:
      return None
    return json.loads(row[0])
