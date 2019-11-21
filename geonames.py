import requests
import sqlite3

class GeoName:

  def __init__(self, row=None, json=None):
    if row != None:
      self.name=row[0]
      self.id=row[1]
      self.cc=row[2]
      self.adm1=row[3]
      self.fcl = 'P'
      self.lat = row[4]
      self.lng=row[5]
      self.population=row[6]
    elif json != None:
      self.id = json['geonameId']
      self.name = json['name']
      self.population = json['population']
      self.fcl = json['fcl']
      self.lat = float(json['lat'])
      self.lng = float(json['lng'])
      self.cc = '-' if 'countryCode' not in json else json['countryCode']
      self.adm1 = '-' if 'adminCode1' not in json else json['adminCode1']


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

  def __init__(self):
    self.matches = []
    self.hierarchy = []
    self.score = 0
    self.local_matches = []
    self.confidence = 0

  def size(self):
    return len(self.matches)

  def description(self):
    path = ' > '.join(m.name for m in self.hierarchy)
    name = ' + '.join(m.name for m in self.matches)
    return path + ' > ' + name

  def identifier(self):
    sorted_ids = sorted(str(m.geoname.id) for m in self.matches)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(m.geoname.population for m in self.matches)

  def bounding_boxes(self, d=0.1):
    bounding_boxes = []
    for match in self.matches:
      bounding_boxes.append(match.bounding_box(d))
    return bounding_boxes


class GeoNamesMatcher:

  def generate_clusters(self, entity_names, limit):
    matches = self.derive_matches(entity_names)
    clusters = self.find_clusters(matches, entity_names)
    return self.select_best_clusters(clusters, limit)

  def derive_matches(self, entity_names):
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

  def find_clusters(self, matches, entity_names):
    clusters = []
    unbound = matches

    while len(unbound) > 0:
      seed = unbound.pop()

      # find all other matches in the same ADM1 area
      peers = {}
      g1 = seed.geoname
      for other in unbound:
        g2 = other.geoname
        if g1.cc != g2.cc or g1.adm1 != g2.adm1:
            continue
        bucket = [] if other.name not in peers else peers[other.name]
        bucket.append(other)
        peers[other.name] = bucket

      cluster = MatchCluster()

      # add smallest match for each name to cluster
      cluster.matches.append(seed)
      for matches in peers.values():
        smallest = min(matches, key=lambda n: n.geoname.population)
        cluster.matches.append(smallest)
        for m in matches:
          unbound.remove(m)

      # add the hierarchy above the largest clustered match
      largest = max(cluster.matches, key=lambda n: n.geoname.population)
      geoname_hierarchy = GeoNamesAPI.get_hierarchy(largest.geoname.id)[
          1:-1]
      for geoname in geoname_hierarchy[1:-1]:  # skip Earth and match itself
        positions = []
        if geoname.name in entity_names:
          positions = entity_names[geoname.name]
        match = GeoNameMatch(geoname, positions)
        cluster.hierarchy.append(match)

      clusters.append(cluster)

    return clusters

  def select_best_clusters(self, clusters, limit):

    for cluster in clusters:
      cluster.score = sum(len(m.positions) for m in cluster.matches)
      cluster_names = [m.name for m in cluster.matches]
      previous_names = []
      for match in cluster.hierarchy:
        if match.name not in cluster_names and match.name not in previous_names:
          cluster.score += 2 * len(match.positions)
          previous_names.append(match.name)

    sorted_clusters = sorted(clusters, key=lambda c: c.score, reverse=True)
    num = min(limit, len(clusters))
    return sorted_clusters[0:num]


class GeoNamesAPI:

  @staticmethod
  def get_hierarchy(id):
    json_dict = GeoNamesAPI.get_json('hierarchy', id)
    geonames_array = json_dict['geonames']
    return list(map(lambda d: GeoName(json=d), geonames_array))

  @staticmethod
  def get_geoname(id):
    json_dict = GeoNamesAPI.get_json('get', id)
    return GeoName(json=json_dict)

  @staticmethod
  def get_json(endpoint, id):
    url = f'http://api.geonames.org/{endpoint}JSON?geonameId={id}&username=map2txt'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return res.json()
