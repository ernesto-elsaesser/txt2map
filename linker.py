import re
import geonames


class TreeRoot:

  def __init__(self):
    self.children = {}


class TreeNode:

  def __init__(self, geoname, mentions):
    self.geoname = geoname
    self.mentions = mentions
    self.ancestor = None
    self.children = {}


class NodeCluster:

  def __init__(self, nodes, ancestor):
    self.nodes = nodes
    self.ancestors = []
    next_ancestor = ancestor
    while isinstance(next_ancestor, TreeNode):
      self.ancestors.insert(0, next_ancestor)
      next_ancestor = next_ancestor.ancestor
    self.matches = []
    self.confidence = 0

  def size(self): return len(self.nodes)

  def ancestor_mentions(self):
    return sum(a.mentions for a in self.ancestors)

  def total_mentions(self):
    return sum(n.mentions for n in self.nodes) + self.ancestor_mentions()

  def path(self):
    ancestor_str = ' > '.join(a.geoname.name for a in self.ancestors)
    cluster_str = ' + '.join(n.geoname.name for n in self.nodes)
    return ancestor_str + ' > ' + cluster_str

  def identifier(self):
    sorted_ids = sorted(str(n.geoname.id) for n in self.nodes)
    return '-'.join(sorted_ids)

  def bounding_boxes(self, d=0.1):
    bounding_boxes = []
    for node in self.nodes:
      g = node.geoname
      bounding_box = [g.lat - d, g.lng - d, g.lat + d, g.lng + d]
      bounding_boxes.append(bounding_box)
    return bounding_boxes

  def population(self):
    return sum(n.geoname.population for n in self.nodes)


class GeoLinker:

  def __init__(self):
    self.geonames_client = geonames.GeoNamesClient()

  def create_clusters(self, matches, db, text):
    leafs = self.build_ancestor_tree(matches, db, text)
    clusters = self.cluster_leafs(leafs)
    return sorted(clusters, key=lambda c: c.total_mentions(), reverse=True)

  def build_ancestor_tree(self, matches, db, text):
    root = TreeRoot()
    leafs = []

    for name in matches:
      geoname_ids = db.get_geoname_ids(name)
      for geoname_id in geoname_ids:
        hierarchy = self.geonames_client.get_hierarchy(geoname_id)

        ancestor = root
        for geoname in hierarchy[1:]:
          if geoname.id in ancestor.children:
            ancestor = ancestor.children[geoname.id]
          else:
            if geoname.id == geoname_id:
              mentions = len(matches[name])
            else:
              mentions = self.count_mentions(geoname.name, text)
            node = TreeNode(geoname, mentions)
            node.ancestor = ancestor
            ancestor.children[geoname.id] = node
            ancestor = node

        leafs.append(ancestor)

    return leafs

  def cluster_leafs(self, leafs):
    unclustered = leafs
    clusters = []
    while len(unclustered) > 0:
      node = unclustered[0]
      cluster_ancestor = node.ancestor
      while not self.spans_cluster(cluster_ancestor):
        cluster_ancestor = cluster_ancestor.ancestor
      leafs = self.leafs_below(cluster_ancestor)
      for leaf in leafs: unclustered.remove(leaf)
      cluster = NodeCluster(leafs, cluster_ancestor)
      if cluster.population() > 100_000 or cluster.size() > 1 or cluster.ancestor_mentions() > 1:
        clusters.append(cluster)

    return clusters

  def spans_cluster(self, node):
    code = node.geoname.feature_code
    if code.startswith('PCL'): return True
    return code == 'ADM1'

  def leafs_below(self, node):
    if len(node.children) == 0:
      return [node]
    child_nodes = node.children.values()
    return sum((self.leafs_below(n) for n in child_nodes), [])

  def calculate_confidences(self, clusters):

    if len(clusters) == 0:
      return clusters

    for cluster in clusters:
      if cluster.size() > 1:
        cluster.confidence += 0.3
      if len(cluster.matches) > 1:
        cluster.confidence += 0.3

    most_matches = max(clusters, key=lambda c: len(c.matches))
    if len(most_matches.matches) > 0:
      most_matches.confidence += 0.3

    biggest_population = max(clusters, key=lambda c: c.population())
    biggest_population.confidence += 0.1

    return sorted(clusters, key=lambda c: c.confidence, reverse=True)

  def count_mentions(self, word, text):
    occurrences = re.findall(word, text)
    return len(occurrences)
