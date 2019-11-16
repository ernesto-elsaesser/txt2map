import logging
import regex
import csv
import geonames
import osm
import linker


class Match:

  def __init__(self, name, positions, refs):
    self.name = name
    self.positions = positions
    self.refs = refs


class Geoparser:

  max_osm_queries_per_request = 5

  def __init__(self):
    self.linker = linker.GeoLinker()
    self.osm_client = osm.OverpassClient()
    self.anchor_re = regex.compile(r'\s\p{Lu}(\.)*[^\s\.!?,:;\)"\']+')

    self.abbreviations = []
    reader = csv.reader(open('data/abbreviations.txt'), delimiter=' ')
    for row in reader:
      re = regex.compile(row[0])
      self.abbreviations.append((re, row[1]))

    with open('data/stopwords.txt') as f:
      self.stopwords = f.read().split('\n')

  def parse(self, text):

    padded_text = text + ' ' # also catch matches in last word

    anchors = []
    for match in self.anchor_re.finditer(' ' + text):
      (start, end) = match.span()
      end -= 1  # correct for initial ' '
      lower_span = text[start:end].lower()
      if lower_span not in self.stopwords:
        anchors.append((start, end))

    logging.info('parsing on global level ...')
    geonames_db = geonames.GeoNamesDatabase()
    geonames_matches = self.find_names(padded_text, anchors, geonames_db)
    context_list = self.linker.build_context_list(geonames_matches, geonames_db)
    clusters = self.linker.cluster_context_list(context_list)

    osm_query_count = 0
    for cluster in clusters:
      if osm_query_count > self.max_osm_queries_per_request:
        logging.info('aborted parsing after %s OSM queries', osm_query_count)
        break

      if len(cluster.clustered_bounds) == 0:
        continue

      logging.info('entering local level: %s ', cluster.context_path())
      osm_query_count += 1
      osm_db = self.osm_client.load_name_database(cluster)

      logging.info('parsing on local level ...')
      osm_matches = self.find_names(padded_text, anchors, osm_db, True)
      for name, positions in osm_matches.items():
          refs = osm_db.get_refs(name)
          logging.info('OSM match: %s', name)
          match = Match(name, positions, refs)
          cluster.matches.append(match)

    logging.info('finished.')
    return clusters

  def find_names(self, text, anchors, db, find_abbrvs=False):
    matches = {}
    text_len = len(text)
    prev_match_end = 0
    suffixes_for_prefixes = {}

    for start, end in anchors:
      if start < prev_match_end:
        continue

      prefix = text[start:end]
      if prefix in suffixes_for_prefixes:
        suffixes = suffixes_for_prefixes[prefix]
      else:
        suffixes = self.get_suffixes(prefix, db, find_abbrvs)
        suffixes_for_prefixes[prefix] = suffixes

      text_pos = end
      longest_match = None
      while text_pos < text_len and len(suffixes) > 0:
        next_char = text[text_pos]
        trimmed_suffixes = []
        for name, suffix in suffixes:
          if suffix == '':
            longest_match = name
          elif suffix[0] == next_char:
            trimmed_suffixes.append((name, suffix[1:]))
        suffixes = trimmed_suffixes
        text_pos += 1

      if longest_match != None:
        prev_match_end = text_pos
        if longest_match not in matches:
          matches[longest_match] = []
        matches[longest_match].append(start)

    return matches

  def get_suffixes(self, prefix, db, find_abbrvs):
    found_names = db.find_names(prefix)
    suffixes = []
    for name in found_names:
      suffix = name[len(prefix):]
      suffixes.append((name, suffix))
      if find_abbrvs:
        short_version = self.abbreviated(suffix)
        if short_version != suffix:
          suffixes.append((name, short_version))
    return suffixes
  
  def abbreviated(self, name):
    short_version = name
    for re, repl in self.abbreviations:
      short_version = re.sub(repl, short_version)
    return short_version
