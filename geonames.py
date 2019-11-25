import requests
import sqlite3
import re

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
    c = self.fclass
    self.above_adm1 = c == 'L' or (c == 'A' and self.fcode.startswith('PCL'))

  def __repr__(self):
    return f'{self.name}, {self.cc} [{self.fcode}]'

class Toponym:

  def __init__(self, name, positions):
    self.name = name
    self.positions = positions
    self.candidates = []

  def __repr__(self):
    return self.name

class GeoNameCandidate:

  def __init__(self, geoname, hierarchy, mentions):
    self.geoname = geoname
    self.hierarchy = hierarchy
    self.mentions = mentions

  def center(self):
    return [self.geoname.lat, self.geoname.lng]

  def bounding_box(self, d):
    return [self.geoname.lat - d, self.geoname.lng - d, 
            self.geoname.lat + d, self.geoname.lng + d]

  def __repr__(self):
    return self.geoname.__repr__()

class GeoNamesCluster:

  def __init__(self, candidates, anchor):
    self.candidates = candidates
    self.path = [g.name for g in anchor.hierarchy]
    self.size = len(candidates)
    self.mentions = max(map(lambda c: c.mentions, candidates))
    self.local_matches = []
    self.confidence = 0

  def identifier(self):
    sorted_ids = sorted(str(m.geoname.id) for m in self.candidates)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(m.geoname.population for m in self.candidates)

  def bounding_boxes(self, d=0.1):
    return [m.bounding_box(d) for m in self.candidates]

  def __repr__(self):
    return ' > '.join(self.path[1:]) # skip Earth

class GeoNamesMatcher:

  def __init__(self, text):
    self.text = text
    self.mention_cache = {}

  def generate_clusters(self, toponyms):
    self.get_candidates(toponyms)
    selected_candidates = self.select_candidates(toponyms)
    return self.cluster_candidates(selected_candidates)

  def get_candidates(self, toponyms):
    for toponym in toponyms:
      geonames = GeoNamesAPI.search(toponym.name)
      geonames = [g for g in geonames if g.name == toponym.name]
      for geoname in geonames:
        hierarchy = GeoNamesAPI.get_hierarchy(geoname.id)
        mentions = 0
        for ancestor in hierarchy:
          mentions += self.count_mentions(ancestor.name)
        candidate = GeoNameCandidate(geoname, hierarchy, mentions)
        toponym.candidates.append(candidate)

  def count_mentions(self, name):
    if name in self.mention_cache:
      return self.mention_cache[name]
    mentions = re.findall(name, self.text, re.IGNORECASE)
    self.mention_cache[name] = len(mentions)
    return len(mentions)

  def select_candidates(self, toponyms):
    selected_candidates = []
    for toponym in toponyms:
      if len(toponym.candidates) == 0:
        continue
      max_m = max(toponym.candidates, key=lambda c: c.mentions)
      max_mentions = [c for c in toponym.candidates if c.mentions == max_m.mentions]
      selected_candidates.append(max_mentions[0])
    return selected_candidates

  def cluster_candidates(self, candidates):
    seeds = list(sorted(candidates, key=lambda m: m.geoname.population, reverse=True))

    clusters = []
    linked_ids = set()

    while len(seeds) > 0:
      seed = seeds.pop()
      linked_ids.add(seed.geoname.id)

      # find all matches in the same ADM1 area
      connected = [seed]
      hierarchy_ids = [g.id for g in seed.hierarchy]
      g1 = seed.geoname
      for other_candidate in candidates:
        g2 = other_candidate.geoname
        if g2.id in linked_ids:
          continue
        if g1.cc == g2.cc and g1.adm1 == g2.adm1:
          connected.append(other_candidate)
          linked_ids.add(g2.id)
          seeds.remove(other_candidate)
        elif g2.id in hierarchy_ids:
          connected.append(other_candidate)
          seeds.remove(other_candidate)

      cities = [c for c in connected if c.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda c: c.geoname.population)
      else:
        anchor = min(connected, key=lambda c: c.geoname.population)

      cluster = GeoNamesCluster(connected, anchor)
      clusters.append(cluster)

    return sorted(clusters, key=lambda c: c.population(), reverse=True)


class GeoNamesAPI:

  @staticmethod
  def search(name):
    params = [('name_equals', name), ('maxRows', 3)]
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
