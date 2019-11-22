import requests
import sqlite3

class GeoName:

  def __init__(self, row=None, json=None):
    if row != None:
      self.name = row[0]
      self.id = row[1]
      self.lat = row[2]
      self.lng = row[3]
      self.fcode = row[4]
      self.cc = row[5]
      self.adm1 = row[6]
      self.population = row[7]
    elif json != None:
      self.id = json['geonameId']
      self.name = json['name']
      self.population = json['population']
      self.fcode = json['fcode']
      self.lat = float(json['lat'])
      self.lng = float(json['lng'])
      self.cc = '-' if 'countryCode' not in json else json['countryCode']
      self.adm1 = '-' if 'adminCode1' not in json else json['adminCode1']

    c = self.fcode
    self.is_city = c.startswith('PP')
    # Earth, continents, countries:
    self.above_adm1 = c == 'CONT' or c.startswith('PCL') or self.id == 6295630

class GeoNameMatch:

  def __init__(self, geoname, positions):
    self.geoname = geoname
    self.name = geoname.name
    self.positions = positions

  def center(self):
    return [self.geoname.lat, self.geoname.lng]

  def bounding_box(self, d):
    return [self.geoname.lat - d, self.geoname.lng - d, 
            self.geoname.lat + d, self.geoname.lng + d]


class MatchCluster:

  def __init__(self, cities, all_matches, hierarchy):
    self.cities = cities
    self.non_cities = [m for m in all_matches if m not in cities]
    self.all_matches = all_matches

    self.path = [g.name for g in hierarchy]

    self.match_count = len(all_matches)
    self.city_count = len(cities)

    p_score = sum(len(m.positions) for m in cities)
    a_score = sum(len(m.positions) for m in self.non_cities)
    self.score = p_score * (a_score + 1)  # 0 if no cities

    self.local_matches = []
    self.confidence = 0

  def description(self):
    return ' > '.join(self.path[1:]) # skip Earth

  def identifier(self):
    sorted_ids = sorted(str(m.geoname.id) for m in self.cities)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(m.geoname.population for m in self.cities)

  def bounding_boxes(self, d=0.1):
    return [m.bounding_box(d) for m in self.cities]


class GeoNamesMatcher:

  def generate_clusters(self, entity_names):
    matches = self.get_matches(entity_names)
    return self.find_clusters(matches)

  def get_matches(self, entity_names):
    db = sqlite3.connect('data/geonames.db')
    cursor = db.cursor()
    matches = []

    for name, positions in entity_names.items():
      cursor.execute('SELECT * FROM geonames WHERE name = ?', (name, ))
      for row in cursor.fetchall():
        geoname = GeoName(row=row)
        match = GeoNameMatch(geoname, positions)
        matches.append(match)

    db.close()
    return matches

  def find_clusters(self, matches):
    candidates = [m for m in matches if not m.geoname.above_adm1]
    candidates = sorted(candidates, key=lambda m: m.geoname.population)

    top_level = {}
    for match in matches:
      if match.geoname.above_adm1:
        top_level[match.name] = match
    unlinked_top_levels = list(top_level.keys())

    clusters = []
    linked_matches = set()

    for match in candidates:
      if match in linked_matches:
        continue

      # find all matches in the same ADM1 area
      related_matches = [match]
      linked_matches.add(match)
      g1 = match.geoname
      for other_match in matches:
        if other_match in linked_matches:
          continue
        g2 = other_match.geoname
        if g1.cc == g2.cc and g1.adm1 == g2.adm1:
          related_matches.append(other_match)
          linked_matches.add(other_match)

      cities = [m for m in related_matches if m.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda n: n.geoname.population)
      else:
        anchor = min(related_matches, key=lambda n: n.geoname.population)

      hierarchy = GeoNamesAPI.get_hierarchy(anchor.geoname.id)
      for geoname in hierarchy:
        if geoname.name in top_level:
          related_matches.append(top_level[geoname.name])
          unlinked_top_levels.remove(geoname.name)

      cluster = MatchCluster(cities, related_matches, hierarchy)
      clusters.append(cluster)

    for name in unlinked_top_levels:
      match = top_level[name]
      hierarchy = GeoNamesAPI.get_hierarchy(match.geoname.id)
      cluster = MatchCluster([], [match], hierarchy)
      clusters.append(cluster)

    return clusters


class GeoNamesAPI:

  @staticmethod
  def get_hierarchy(id):
    params = {'geonameId': id}
    json_dict = GeoNamesAPI.get_json('hierarchy', params)
    geonames = []
    if 'geonames' in json_dict:
      json_array = json_dict['geonames']
      geonames = list(map(lambda d: GeoName(json=d), json_array))
    return geonames

  @staticmethod
  def get_geoname(id):
    params = {'geonameId': id}
    json_dict = GeoNamesAPI.get_json('get', params)
    return GeoName(json=json_dict)

  @staticmethod
  def get_children(id):
    params = {'geonameId': id, 'maxRows': 250}
    json_dict = GeoNamesAPI.get_json('children', params)
    geonames = []
    if 'geonames' in json_dict:
      json_array = json_dict['geonames']
      geonames = list(map(lambda d: GeoName(json=d), json_array))
    return geonames

  @staticmethod
  def get_json(endpoint, params):
    url = f'http://api.geonames.org/{endpoint}JSON?username=map2txt'
    for key in params:
      url += f'&{key}={params[key]}'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return res.json()
