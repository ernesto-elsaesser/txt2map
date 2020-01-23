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
      doc.annotate(Layer.lres, a.pos, a.phrase, 'global', a.data)
      resolutions[a.phrase] = Datastore.get_geoname(a.data)
    tree = GeoNamesTree(resolutions)

    entity_indicies = doc.annotations_by_index(Layer.ner)
    seen = []

    for leaf in tree.leafs():
      geonames = leaf.geonames.values()
      anchors = [g for g in geonames if g.is_city]

      if len(anchors) == 0:
        smallest = min(geonames, key=lambda g: g.population)
        anchor = self._find_city_child(smallest)
        if anchor != None:
          anchors.append(anchor)

      anchors = sorted(anchors, key=lambda g: -g.population)
      for anchor in anchors:
        if anchor.id in seen:
          continue
        seen.append(anchor.id)
        print(f'lres - anchor: {anchor}')
        db = Datastore.load_osm_database(anchor)

        def commit_match(c):
          if c.match.isnumeric():
            return False
          replace_identical = False
          if c.pos in entity_indicies:
            ent_ann = entity_indicies[c.pos]
            if len(ent_ann.phrase) > len(c.match):
              return True # part of entity name
            gres_ann = doc.get(Layer.gres, ent_ann.pos)
            if gres_ann != None:
              if gres_ann.data == anchor.id:
                return True # anchor itself
              geoname = Datastore.get_geoname(gres_ann.data)
              if geoname.char_match(c.match):
                return True # exact match
              replace_identical = True
          osm_refs = db.get_elements(c.lookup_phrase)
          print(f'lres - local match: {c.match}')
          doc.annotate(Layer.lres, c.pos, c.match, 'local', osm_refs, replace_shorter=True, replace_identical=replace_identical)
          return True

        self.matcher.find_matches(doc, db.find_names, commit_match)

  def _find_city_child(self, geoname):
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
      