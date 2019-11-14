import geonames


class Context:

  box_side = 0.2

  def __init__(self, hierarchy):
    self.geoname = hierarchy[-1]
    self.hierarchy = hierarchy[:-1]
    self.found_ancestor_ids = []
    self.bounds = None
    if self.geoname.feature_class == 'P':
      d = self.box_side / 2
      self.bounds = [self.geoname.lat - d, self.geoname.lng - d,
                           self.geoname.lat + d, self.geoname.lng + d]

  def ancestor_names(self):
    names = []
    for geoname in self.hierarchy[1:]:
      name = geoname.name
      if geoname.id in self.found_ancestor_ids:
        name += '*'
      names.append(name)
    return names


class ContextCluster:

  def __init__(self, context):
    self.geonames = [context.geoname]
    self.clustered_bounds = [] if context.bounds == None else [context.bounds]
    self.ancestor_names = context.ancestor_names()
    self.matches = []

  def merge_cluster(self, cluster):
    self.geonames += cluster.geonames
    self.clustered_bounds += cluster.clustered_bounds
    i = min(len(self.ancestor_names), len(cluster.ancestor_names))
    while self.ancestor_names[i-1] != cluster.ancestor_names[i-1]:
      i -= 1
    self.ancestor_names = self.ancestor_names[:i]

  def clustered_ids(self):
    return map(lambda g: g.id, self.geonames)

  def clustered_names(self):
    return map(lambda g: g.name, self.geonames)

  def context_path(self):
    ancestor_path = ' > '.join(self.ancestor_names)
    joined_names = ' + '.join(self.clustered_names())
    return ancestor_path + ' > ' + joined_names

  def identifier(self):
    return '-'.join(str(sorted(self.clustered_ids())))


class GeoLinker:

  def __init__(self):
    self.geonames_client = geonames.GeoNamesClient()

  def build_context_list(self, matches, db):

    context_map = {}
    for name in matches:
      geoname_ids = db.get_geoname_ids(name)
      for geoname_id in geoname_ids:
        hierarchy = self.geonames_client.get_hierarchy(geoname_id)
        context = Context(hierarchy)
        context_map[context.geoname.id] = context

    all_contexts = list(context_map.values())
    all_ids = list(context_map.keys())
    for context in all_contexts:
      for ancestor in context.hierarchy:
        if ancestor.id in all_ids:
          context.found_ancestor_ids.append(ancestor.id)
          # remove A level contexts with are ancestors of others
          if ancestor.id in context_map and context_map[ancestor.id].bounds == None:
            del context_map[ancestor.id]

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

    return clusters

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
