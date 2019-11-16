import geonames

class Ancestor:

  def __init__(self, geoname):
    self.name = geoname.name
    self.id = geoname.id
    self.mentions = 0


class Context:

  box_side = 0.2

  def __init__(self, hierarchy, mentions):
    self.geoname = hierarchy[-1]
    self.ancestors = list(map(lambda g: Ancestor(g), hierarchy[:-1]))
    self.mentions = mentions

    if self.geoname.feature_class == 'P':
      d = self.box_side / 2
      self.bounds = [self.geoname.lat - d, self.geoname.lng - d,
                     self.geoname.lat + d, self.geoname.lng + d]
    else:
      self.bounds = None


class ContextCluster:

  def __init__(self, context):
    self.geonames = [context.geoname]
    self.clustered_bounds = [] if context.bounds == None else [context.bounds]
    self.ancestors = context.ancestors
    self.mentions = context.mentions
    self.matches = []

  def merge_cluster(self, cluster):
    self.geonames += cluster.geonames
    self.clustered_bounds += cluster.clustered_bounds
    i = min(len(self.ancestors), len(cluster.ancestors))
    while self.ancestors[i-1].id != cluster.ancestors[i-1].id:
      i -= 1
    self.ancestors = self.ancestors[:i]
    self.mentions += cluster.mentions

  def relevance(self):
    total_ancestor_mentions = sum(map(lambda a: a.mentions , self.ancestors))
    return self.mentions + total_ancestor_mentions

  def context_path(self):
    names = map(lambda g: g.name, self.geonames)
    ancestor_names = map(lambda g: g.name, self.ancestors[1:])
    ancestor_path = ' > '.join(ancestor_names)
    clustered_names = ' + '.join(names)
    return ancestor_path + ' > ' + clustered_names

  def identifier(self):
    sorted_ids = sorted(map(lambda g: str(g.id), self.geonames))
    return '-'.join(sorted_ids)


class GeoLinker:

  def __init__(self):
    self.geonames_client = geonames.GeoNamesClient()

  def build_context_list(self, matches, db):

    # create context objects
    context_map = {}
    for name in matches:
      geoname_ids = db.get_geoname_ids(name)
      for geoname_id in geoname_ids:
        hierarchy = self.geonames_client.get_hierarchy(geoname_id)
        mentions = len(matches[name])
        context = Context(hierarchy, mentions)
        context_map[context.geoname.id] = context

    # count ancestors mentions
    covered_ids = set()
    for context in context_map.values():
      for ancestor in context.ancestors:
        if ancestor.id in context_map:
          ancestor.mentions = context_map[ancestor.id].mentions
          covered_ids.add(ancestor.id)

    # remove context objects that are in the hierarchy of others
    for ancestor_id in covered_ids:
      if ancestor_id in context_map and context_map[ancestor_id].bounds == None:
        del context_map[ancestor_id]

    return list(context_map.values())

  def cluster_context_list(self, context_list):

    clusters = []
    for context in context_list:
      new_clusters = []
      cluster = ContextCluster(context)

      for other_cluster in clusters:
        overlaps = False
        for bounds in other_cluster.clustered_bounds:
          if self.bounding_boxes_overlap(context.bounds, bounds):
            overlaps = True
            break

        if overlaps:
          cluster.merge_cluster(other_cluster)
        else:
          new_clusters.append(other_cluster)

      new_clusters.append(cluster)
      clusters = new_clusters

    return sorted(clusters, key=lambda c: c.relevance(), reverse=True)

  def bounding_boxes_overlap(self, box1, box2):
    if box1 == None or box2 == None:
      return False
    sw = self.coord_within_bounding_box(box1[0], box1[1], box2)
    nw = self.coord_within_bounding_box(box1[2], box1[1], box2)
    se = self.coord_within_bounding_box(box1[0], box1[3], box2)
    ne = self.coord_within_bounding_box(box1[2], box1[3], box2)
    inside = self.coord_within_bounding_box(box2[0], box2[1], box1)
    return sw or nw or se or ne or inside

  def coord_within_bounding_box(self, lat, lng, box):
    return lat > box[0] and lat < box[2] and lng > box[1] and lng < box[3]
