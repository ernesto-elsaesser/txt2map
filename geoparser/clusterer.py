from .geonames import GeoNamesCache
from .osm import OSMLoader
from .matcher import NameMatcher
from .tree import GeoNamesTree
from .config import Config


class Clusterer:

  def __init__(self):
    self.matcher = NameMatcher()
    self.gns_cache = GeoNamesCache()

  def annotate_clu(self, doc):
    resolutions = {}
    res_by_phrase = {}
    for a in doc.get_all('res'):
      resolutions[a.phrase] = self.gns_cache.get(a.data)
      if a.phrase not in res_by_phrase:
        res_by_phrase[a.phrase] = []
      res_by_phrase[a.phrase].append(a)

    tree = GeoNamesTree(resolutions)
    leafs = tree.leafs()

    for idx, leaf in enumerate(leafs):
      tupels = list(leaf.geonames.items())
      anchors = [g for _, g in tupels if g.is_city]
      if len(anchors) == 0:
        (toponym, geoname) = min(tupels, key=lambda t: t[1].population)
        anchor = self._find_anchor(toponym, geoname)
        if anchor != None:
          anchors.append(anchor)

      cluster_key = f'clu-{idx+1}'
      anchors_ids = [g.id for g in anchors]
      for toponym in leaf.geonames:
        for a in res_by_phrase[toponym]:
          doc.annotate('clu', a.pos, toponym, cluster_key, anchors_ids)

  def _find_anchor(self, toponym, geoname):
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    if len(hierarchy) < 2:
      return None

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        return geoname

      if len(children) == 1:
        child = children[0]
        if child.is_city:
            return child
        geoname = child
        continue

      return None

  def annotate_rec_res(self, doc):
    clust_anchors = {}
    largest_pop = {}
    for a in doc.get_all('clu'):
      if a.group in clust_anchors or len(a.data) == 0:
        continue
      geonames = [self.gns_cache.get(gid) for gid in a.data]
      clust_anchors[a.group] = geonames
      largest_pop[a.group] = max(g.population for g in geonames)

    sorted_keys = sorted(clust_anchors.keys(), key=lambda k: -largest_pop[k])

    entity_indicies = doc.annotations_by_index('ner')
    rec_positions = doc.annotations_by_position('rec')

    for cluster_key in sorted_keys:
      anchors = clust_anchors[cluster_key]
      db = OSMLoader.load_database(anchors)

      def lookup_prefix(prefix):
        return db.find_names(prefix)

      def commit_match(c):
        if ' ' not in c.match:
          if len(c.match) < Config.local_match_min_len:
            return False
          if c.pos in entity_indicies and entity_indicies[c.pos].phrase != c.match:
            return False
        if c.pos in rec_positions and rec_positions[c.pos].phrase == c.match:
          return False
        osm_refs = db.get_elements(c.lookup_phrase)
        doc.annotate('rec', c.pos, c.match, cluster_key, '', replace_shorter=True)
        doc.annotate('res', c.pos, c.match, cluster_key, osm_refs, replace_shorter=True)
        return True

      self.matcher.find_matches(doc, lookup_prefix, commit_match)

