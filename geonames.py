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

  def __repr__(self):
    return f'{self.name}, {self.cc} [{self.fcode}]'

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

  def __repr__(self):
    return self.geoname.__repr__()

class MatchCluster:

  def __init__(self, cities, all_matches, hierarchy):
    self.cities = cities
    self.non_cities = [m for m in all_matches if m not in cities]
    self.all_matches = all_matches
    self.path = [g.name for g in hierarchy]
    self.size = len(all_matches)
    self.city_count = len(cities)
    self.local_matches = []
    self.confidence = 0

  def identifier(self):
    sorted_ids = sorted(str(m.geoname.id) for m in self.cities)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(m.geoname.population for m in self.cities)

  def bounding_boxes(self, d=0.1):
    return [m.bounding_box(d) for m in self.cities]

  def __repr__(self):
    return ' > '.join(self.path[1:]) # skip Earth

class GeoNamesMatcher:

  def generate_clusters(self, entity_names):
    matches = self.get_matches(entity_names)
    clusters = self.find_clusters(matches)
    return self.disambiguate(clusters, entity_names)

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
        top_level[match.geoname.id] = match
    unlinked_top_levels_ids = list(top_level.keys())

    clusters = []
    linked_ids = set()

    for match in candidates:
      if match.geoname.id in linked_ids:
        continue

      # find all matches in the same ADM1 area
      related_matches = [match]
      linked_ids.add(match.geoname.id)
      g1 = match.geoname
      for other_match in candidates:
        g2 = other_match.geoname
        if not g2.id in linked_ids and g1.cc == g2.cc and g1.adm1 == g2.adm1:
          related_matches.append(other_match)
          linked_ids.add(g2.id)

      cities = [m for m in related_matches if m.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda n: n.geoname.population)
      else:
        anchor = min(related_matches, key=lambda n: n.geoname.population)

      hierarchy = GeoNamesAPI.get_hierarchy(anchor.geoname.id)
      for geoname in hierarchy:
        if geoname.id in top_level:
          related_matches.append(top_level[geoname.id])
          if geoname.id in unlinked_top_levels_ids:
            unlinked_top_levels_ids.remove(geoname.id)

      cluster = MatchCluster(cities, related_matches, hierarchy)
      clusters.append(cluster)

    for geoname_id in unlinked_top_levels_ids:
      match = top_level[geoname_id]
      hierarchy = GeoNamesAPI.get_hierarchy(geoname_id)
      cluster = MatchCluster([], [match], hierarchy)
      clusters.append(cluster)

    return clusters

  def disambiguate(self, clusters, entity_names):
    cluster_options = {}
    for cluster in clusters:
      all_names = set(m.name for m in cluster.all_matches)
      cluster.score = len(all_names)
      if cluster.city_count > 0:
        cluster.score *= 2

      for name in all_names:
        if name in cluster_options:
          cluster_options[name].append(cluster)
        else:
          cluster_options[name] = [cluster]

    sorted_names = sorted(cluster_options.keys(), reverse=True,
                          key=lambda n: len(entity_names[n]))
    best_clusters = []
    for name in sorted_names:
      options = cluster_options[name]
      best = max(options, key=lambda c: c.score)
      best_options = [c for c in options if c.score == best.score]
      selected = max(best_options, key=lambda c: c.population())
      if selected not in best_clusters:
        best_clusters.append(selected)
    return best_clusters


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
