import logging
import hashlib
import model
import geonames
import osm

class Geoparser:

  def __init__(self):
    self.geonames_client = geonames.GeoNamesClient()
    self.osm_client = osm.OverpassClient()

  def parse(self, text):
    doc = model.Document(text)

    logging.info('parsing on global level ...')
    geonames_db = geonames.GeoNamesDatabase()
    geonames_matches = self.find_names(doc, geonames_db)
    clusters = self.get_bounding_box_clusters(geonames_matches, geonames_db)

    all_matches = []
    for context, boxes in clusters:
      logging.info('entering local context: %s ', context)
      db_identifier = self.hash_for_context(context)
      osm_db = osm.OSMDatabase(db_identifier)

      if not osm_db.data_exists:
        logging.info('loading OSM data ...')
        osm_db.create_tables()
        self.osm_client.load_all_names(boxes, osm_db)

      logging.info('parsing on local level ...')
      osm_matches = self.find_names(doc, osm_db)
      for name, positions in osm_matches.items():
          refs = osm_db.get_refs(name)
          logging.info('OSM match: %s', name)
          match = model.Match(name, positions, refs, context)
          all_matches.append(match)

    logging.info('finished.')
    return all_matches

  def find_names(self, doc, db):
    matches = {}
    prev_match_end = 0

    names_for_anchor = {}

    for anchor, start, end in doc.anchors:
      if start < prev_match_end:
        continue

      if anchor in names_for_anchor:
        found_names = names_for_anchor[anchor]
      else:
        found_names = db.find_names(anchor)

      suffixes = {}
      for name in found_names:
        suffixes[name] = name[len(anchor):]

      text_pos = end
      longest_match = None
      while text_pos < doc.l and len(suffixes) > 0:
        next_char = doc.text[text_pos]
        names = list(suffixes.keys())
        for name in names:
          suffix = suffixes[name]
          if suffix == '':
            del suffixes[name]
            longest_match = name
          elif suffix[0] != next_char:
            del suffixes[name]
          else:
            suffixes[name] = suffix[1:]
        text_pos += 1

      if longest_match != None:
        prev_match_end = text_pos
        if longest_match not in matches:
          matches[longest_match] = []
        matches[longest_match].append(start)

    return matches

  def get_bounding_box_clusters(self, matches, db):

    bounding_boxes = {}
    names = {}
    for name in matches:
      geoname_ids = db.get_geoname_ids(name)
      for geoname_id in geoname_ids:
        geoname = self.geonames_client.get_geoname(geoname_id)
        fcl = geoname['fcl']
        if fcl != 'P':
          continue # TODO: use As for disambiguation
        lat = float(geoname['lat'])
        lng = float(geoname['lng'])
        # TODO: utilize GeoName data: fcode, countryCode, adminName1-3, population, bbox, ...
        bounding_boxes[geoname_id] = self.bounds_around(lat, lng, 0.1)
        names[geoname_id] = name

    clusters = []
    for geoname_id in names:
      new_clusters = []
      box = bounding_boxes[geoname_id]
      cluster_names = [names[geoname_id]]
      cluster_boxes = [box]

      for other_names, other_boxes in clusters:
        overlaps = False
        for other_box in other_boxes:
          if self.bounding_boxes_overlap(box, other_box):
            overlaps = True
            break

        if overlaps:
          cluster_names += other_names
          cluster_boxes += other_boxes
        else:
          new_clusters.append((other_names, other_boxes))

      new_clusters.append((cluster_names, cluster_boxes))
      clusters = new_clusters

    return clusters

  def bounding_boxes_overlap(self, box1, box2):
    sw = self.coord_within_bounding_box(box1[0], box1[1], box2)
    nw = self.coord_within_bounding_box(box1[2], box1[1], box2)
    se = self.coord_within_bounding_box(box1[0], box1[3], box2)
    ne = self.coord_within_bounding_box(box1[2], box1[3], box2)
    inside = self.coord_within_bounding_box(box2[0], box2[1], box1)
    return sw or nw or se or ne or inside

  def coord_within_bounding_box(self, lat, lng, box):
    return lat > box[0] and lat < box[2] and lng > box[1] and lng < box[3]

  def bounds_around(self, lat, lng, delta):
    return [lat - delta, lng - delta, lat + delta, lng + delta]

  def hash_for_context(self, context):
    binary = '|'.join(sorted(context)).encode()
    return hashlib.md5(binary).hexdigest()

