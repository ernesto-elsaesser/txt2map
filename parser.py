import logging
import regex
import geonames
import osm
import linker


class Match:

  def __init__(self, name, positions, refs):
    self.name = name
    self.positions = positions
    self.refs = refs


class Geoparser:

  def __init__(self):
    self.linker = linker.GeoLinker()
    self.osm_client = osm.OverpassClient()
    self.anchor_re = regex.compile(r'\s\p{Lu}(\.)*[^\s\.!?,:;\)"\']+')
    with open('data/stopwords.txt') as f:
      self.stopwords = f.read().split('\n')

  def parse(self, text):

    anchors = []
    for match in self.anchor_re.finditer(' ' + text):
      (start, end) = match.span()
      end -= 1  # correct for initial ' '
      lower_span = text[start:end].lower()
      if lower_span not in self.stopwords:
        anchors.append((start, end))

    logging.info('parsing on global level ...')
    geonames_db = geonames.GeoNamesDatabase()
    geonames_matches = self.find_names(text, anchors, geonames_db)
    context_list = self.linker.build_context_list(geonames_matches, geonames_db)
    clusters = self.linker.cluster_context_list(context_list)

    for cluster in clusters:
      if len(cluster.clustered_bounds) == 0:
        continue

      logging.info('entering local level: %s ', cluster.context_path())
      osm_db = osm.OSMDatabase(cluster.identifier())

      if not osm_db.data_exists:
        logging.info('loading OSM data ...')
        osm_db.create_tables()
        self.osm_client.load_all_names(cluster.clustered_bounds, osm_db)

      logging.info('parsing on local level ...')
      osm_matches = self.find_names(text, anchors, osm_db)
      for name, positions in osm_matches.items():
          refs = osm_db.get_refs(name)
          logging.info('OSM match: %s', name)
          match = Match(name, positions, refs)
          cluster.matches.append(match)

    logging.info('finished.')
    return clusters

  def find_names(self, text, anchors, db):
    matches = {}
    text_len = len(text)
    prev_match_end = 0

    names_for_prefixes = {}

    for start, end in anchors:
      if start < prev_match_end:
        continue

      prefix = text[start:end]
      if prefix in names_for_prefixes:
        found_names = names_for_prefixes[prefix]
      else:
        found_names = db.find_names(prefix)
        names_for_prefixes[prefix] = found_names

      suffixes = {}
      for name in found_names:
        suffixes[name] = name[len(prefix):]

      text_pos = end
      longest_match = None
      while text_pos < text_len and len(suffixes) > 0:
        next_char = text[text_pos]
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
