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


class GraphNode:

  def __init__(self, geoname, name):
    self.geoname = geoname
    self.name = name
    self.links = []

  def bounding_box(self, d):
    return [self.geoname.lat - d, self.geoname.lng - d, 
            self.geoname.lat + d, self.geoname.lng + d]


class NodeCluster:

  def __init__(self, nodes, hierarchy):
    self.nodes = nodes
    self.hierarchy = hierarchy
    self.size = len(nodes)
    self.score = 0
    self.matches = []
    self.confidence = 0

  def description(self):
    path = ' > '.join(n.name for n in self.hierarchy)
    name = ' + '.join(n.name for n in self.nodes)
    return path + ' > ' + name

  def identifier(self):
    sorted_ids = sorted(str(n.geoname.id) for n in self.nodes)
    return '-'.join(sorted_ids)

  def population(self):
    return sum(n.geoname.population for n in self.nodes)

  def bounding_boxes(self, d=0.1):
    bounding_boxes = []
    for node in self.nodes:
      bounding_boxes.append(node.bounding_box(d))
    return bounding_boxes


class GeoNamesClient:

  api_url = 'http://api.geonames.org'

  def generate_clusters(self, entity_names, limit):
    graph_nodes = self.create_nodes(entity_names)
    clusters = self.find_clusters(graph_nodes)
    return self.find_best_clusters(clusters, entity_names, limit)

  def create_nodes(self, entity_names):
    db = sqlite3.connect('data/geonames.db')
    cursor = db.cursor()
    graph_nodes = []

    for name in entity_names:
      cursor.execute('SELECT * FROM geonames WHERE name = ?', (name, ))
      for row in cursor.fetchall():
        geoname = GeoName(row=row)
        graph_nodes.append(GraphNode(geoname, name))

    db.close()

    return graph_nodes

  def find_clusters(self, graph_nodes):
    clusters = []
    unbound = graph_nodes

    while len(unbound) > 0:
      seed = unbound.pop()
      connected = {}
      g1 = seed.geoname
      for node in unbound:
        g2 = node.geoname
        if g1.cc != g2.cc or g1.adm1 != g2.adm1:
            continue
        bucket = [] if node.name not in connected else connected[node.name]
        bucket.append(node)
        connected[node.name] = bucket

      cluster_nodes = [seed]
      for nodes in connected.values():
        smallest_node = min(nodes, key=lambda n: n.geoname.population)
        for n in nodes: unbound.remove(n)
        cluster_nodes.append(smallest_node)

      biggest_node = max(cluster_nodes, key=lambda n: n.geoname.population)
      hierarchy = self.get_hierarchy(biggest_node.geoname.id)

      cluster = NodeCluster(cluster_nodes, hierarchy[1:-1])
      clusters.append(cluster)

    return clusters

  def find_best_clusters(self, clusters, entity_names, limit):

    for cluster in clusters:
      score = sum(entity_names[n.name] for n in cluster.nodes)
      for geoname in cluster.hierarchy:
        if geoname.name in entity_names:
          score += entity_names[geoname.name] * 2
      cluster.score = score

    sorted_clusters = sorted(clusters, key=lambda c: c.score, reverse=True)
    num = min(limit, len(clusters))
    return sorted_clusters[0:num]

  def get_hierarchy(self, id):
    url = f'{self.api_url}/hierarchyJSON?geonameId={id}&username=map2txt'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    json_dict = res.json()
    geonames_array = json_dict['geonames']
    return list(map(lambda d: GeoName(json=d), geonames_array))

  def calculate_confidences(self, clusters):

    if len(clusters) == 0:
      return clusters

    for cluster in clusters:
      if cluster.size > 2:
        cluster.confidence += 0.4
      elif cluster.size > 1:
        cluster.confidence += 0.2
      if len(cluster.matches) > 1:
        cluster.confidence += 0.3

    most_matches = max(clusters, key=lambda c: len(c.matches))
    if len(most_matches.matches) > 0:
      most_matches.confidence += 0.2

    biggest_population = max(clusters, key=lambda c: c.population())
    biggest_population.confidence += 0.1

    return sorted(clusters, key=lambda c: c.confidence, reverse=True)
