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

    self.is_adm = not self.fcode.startswith('PP')
    self.is_adm1 = self.fcode.startswith('ADM1')
    self.is_country = self.fcode.startswith('PCL')
  

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

  def __init__(self, p_matches, a_matches, path_anchor):
    self.p_matches = p_matches
    self.a_matches = a_matches

    hierarchy = GeoNamesAPI.get_hierarchy(path_anchor.geoname.id)
    self.path = [g.name for g in hierarchy[1:]] # skip Earth

    self.match_count = len(p_matches + a_matches)
    self.size = len(p_matches)

    p_score = sum(len(m.positions) for m in p_matches)
    a_score = sum(len(m.positions) for m in a_matches)
    self.score = p_score * (a_score + 1)  # as with no ps don't count

    self.local_matches = []
    self.confidence = 0

  def description(self):
    return ' > '.join(self.path)

  def identifier(self):
    sorted_ids = sorted(str(m.geoname.id) for m in self.p_matches)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(m.geoname.population for m in self.p_matches)

  def bounding_boxes(self, d=0.1):
    return [m.bounding_box(d) for m in self.p_matches]


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
    sorted_matches = sorted(matches, key=lambda m: m.geoname.population)
    clusters = []
    bound_matches = set()
    covered_countries = set()

    for match in sorted_matches:
      if match in bound_matches or match in covered_countries:
        continue

      # find all matches in the same ADM1 area
      related_matches = [match]
      g1 = match.geoname
      for other_match in matches:
        if other_match is match:
          continue
        g2 = other_match.geoname
        if g2.is_country:
          if g1.cc == g2.cc:
            related_matches.append(other_match)
            covered_countries.add(other_match)
        elif other_match not in bound_matches:
          if g1.cc == g2.cc and g1.adm1 == g2.adm1:
            related_matches.append(other_match)
            bound_matches.add(other_match)

      p_matches = [m for m in related_matches if not m.geoname.is_adm]
      a_matches = [m for m in related_matches if m.geoname.is_adm]

      if len(p_matches) > 0:
        anchor = max(p_matches, key=lambda n: n.geoname.population)
      else:
        anchor = min(a_matches, key=lambda n: n.geoname.population)
      cluster = MatchCluster(p_matches, a_matches, anchor)
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
