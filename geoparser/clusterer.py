from .gazetteer import Gazetteer
from .geonames import GeoNamesCache
from .osm import OSMLoader
from .matcher import NameMatcher
from .tree import GeoNamesTree
from .config import Config


class Clusterer:

  def __init__(self):
    self.matcher = NameMatcher()
    self.gns_cache = GeoNamesCache()
    self.top_names = Gazetteer.defaults().keys()

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
    if len(hierarchy) == 1:
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
    clust_keys = {}
    for a in doc.get_all('clu'):
      clust_keys[a.group] = a.data

    entity_indicies = doc.annotations_by_index('ner')
    rec_positions = doc.annotations_by_position('rec')

    for cluster_key, anchor_ids in clust_keys.items():
      if len(anchor_ids) == 0:
        continue

      geonames = [self.gns_cache.get(gid) for gid in anchor_ids]
      db = OSMLoader.load_database(geonames)

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

  def annotate_con(self, doc):
    clust_keys = [l for l in doc.layers() if l.startswith('clu-')]
    clust_count = len(clust_keys)

    if clust_count == 0:
      return

    for clust_key in clust_keys:
      glob_anns = doc.get_all('clu', clust_key)
      loc_anns = doc.get_all(clust_key)
      anchor_ids = glob_anns[0].data
      confidence = 'high'

      if clust_count > 1 and len(glob_anns) == 1 and len(anchor_ids) > 0:
        a = glob_anns[0]
        in_gaz = a.phrase in self.top_names
        if not in_gaz and ' ' not in a.phrase:
          if len(loc_anns) == 0:
            confidence = 'low'

      for a in glob_anns:
        doc.annotate('con', a.pos, a.phrase, confidence, '')
