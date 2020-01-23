from .datastore import Datastore
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .tree import GeoNamesTree


class LocalGeoparser(Step):

  key = 'local'
  layers = [Layer.lres]

  def __init__(self):
    self.matcher = NameMatcher()

  def annotate(self, doc):
    resolutions = {}
    for a in doc.get_all(Layer.gres):
      doc.annotate(Layer.lres, a.pos, a.match, 'global', a.data)
      resolutions[a.phrase] = Datastore.get_geoname(a.data)
    tree = GeoNamesTree(resolutions)

    entity_indicies = doc.annotations_by_index('ner')

    for leaf in tree.leafs():
      items = list(leaf.geonames.items())
      anchors = [g for _, g in items if g.is_city]

      if len(anchors) == 0:
        (toponym, geoname) = min(items, key=lambda t: t[1].population)
        anchor = self._find_anchor(toponym, geoname)
        if anchor != None:
          anchors.append(anchor)

      anchors = sorted(anchors, key=lambda g: -g.population)
      for anchor in anchors:
        db = Datastore.load_osm_database(anchor)

        def commit_match(c):
          if ' ' not in c.match and c.pos in entity_indicies:
            ent_ann = entity_indicies[c.pos]
            if ent_ann.phrase != c.match:
              return False
          osm_refs = db.get_elements(c.lookup_phrase)
          doc.annotate(Layer.lres, c.pos, c.match, cluster_key, osm_refs, replace_shorter=True)
          return True

        self.matcher.find_matches(doc, db.find_names, commit_match)

  def _find_anchor(self, toponym, geoname):
    hierarchy = Datastore.get_hierarchy(geoname.id)
    if len(hierarchy) < 2:
      return None

    while True:
      children = Datastore.get_children(geoname.id)

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
