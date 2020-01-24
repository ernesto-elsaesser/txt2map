from .datastore import Datastore
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .tree import GeoNamesTree
from .osm import OverpassAPI
from .util import BoundingBox, GeoUtil


class LocalGeoparser(Step):

  key = 'local'
  layers = [Layer.lres]

  def __init__(self):
    self.matcher = NameMatcher()

  def annotate(self, doc):
    resolutions = {}
    for a in doc.get_all(Layer.gres):
      doc.annotate(Layer.lres, a.pos, a.phrase, 'global', a.data)
      resolutions[a.phrase] = Datastore.get_geoname(a.data[2])
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
        data_cache = {}

        def commit_match(c):
          if c.match.isnumeric():
            return False
          replace_identical = False
          if c.pos in entity_indicies:
            ent_ann = entity_indicies[c.pos]
            if len(ent_ann.phrase) > len(c.match):
              return True # part of entity name
            prev_ann = doc.get(Layer.lres, ent_ann.pos)
            if prev_ann != None:
              if prev_ann.group == 'local':
                return True # already annotated locally
              geoname_id = prev_ann.data[2]
              if geoname_id == anchor.id:
                return True # anchor itself
              geoname = Datastore.get_geoname(geoname_id)
              if geoname.char_match(c.match):
                return True # exact global resolution
              replace_identical = True
          print(f'lres - local match: {c.match}')
          if c.lookup_phrase in data_cache:
            data = data_cache[c.lookup_phrase]
          else:
            osm_elements = db.get_elements(c.lookup_phrase)
            data = self._annotation_data(osm_elements)
            data_cache[c.lookup_phrase] = data
          doc.annotate(Layer.lres, c.pos, c.match, 'local', data, replace_shorter=True, replace_identical=replace_identical)
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

  def _annotation_data(self, osm_elements):
    geoms = Datastore.load_osm_geometries(osm_elements)

    bboxes = [BoundingBox(*geom) for geom in geoms['relation'].values()]
    coords = []

    for bbox in bboxes:
      coords.append((bbox.center_lat, bbox.center_lon))

    for geom in geoms['node'].values():
      if not self._point_in_boxes(*geom, bboxes):
        coords.append((geom[0], geom[1]))

    for geom in geoms['way'].values():
      bbox = BoundingBox(*geom)
      if not self._point_in_boxes(bbox.center_lat, bbox.center_lon, bboxes):
        coords.append((bbox.center_lat, bbox.center_lon))

    (lat, lon) = GeoUtil.average_coord(coords)
    osm_refs = [e.reference for e in osm_elements]

    return [lat, lon, osm_refs]

  def _point_in_boxes(self, lat, lon, boxes):
    for bbox in boxes:
      if GeoUtil.point_in_bounding_box(lat, lon, bbox):
        return True
    return False
          