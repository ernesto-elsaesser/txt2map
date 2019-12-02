import logging
import re
from .model import OSMMatch

class OSMNameMatcher:

  abbrevs = [
      (re.compile('Street'), 'St'),
      (re.compile('Avenue'), 'Ave'),
      (re.compile('Boulevard'), 'Blvd'),
      (re.compile('Freeway'), 'Fwy'),
      (re.compile('Parkway'), 'Pkwy'),
      (re.compile('Lane'), 'Ln'),
      (re.compile('Road'), 'Rd'),
      (re.compile('Square'), 'Sq'),
      (re.compile('Mount'), 'Mt'),
      (re.compile('North'), 'N'),
      (re.compile('East'), 'E'),
      (re.compile('South'), 'S'),
      (re.compile('West'), 'W'),
      (re.compile('Northeast'), 'NE'),
      (re.compile('Southeast'), 'SE'),
      (re.compile('Southwest'), 'SW'),
      (re.compile('Northwest'), 'NW')
  ]

  @staticmethod
  def find_names(text, anchors, osm_db):
    text = text + ' '  # also catch matches in last word
    text_len = len(text)
    names = {}
    prev_match_end = 0
    suffixes_for_prefixes = {}

    for start, end in anchors:
      if start < prev_match_end:
        continue

      prefix = text[start:end]
      if prefix in suffixes_for_prefixes:
        suffixes = suffixes_for_prefixes[prefix]
      else:
        suffixes = OSMNameMatcher.get_suffixes(prefix, osm_db)
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
        if longest_match not in names:
          names[longest_match] = []
        names[longest_match].append(start)

    matches = []
    for name, positions in names.items():
      elements = osm_db.get_elements(name)
      match = OSMMatch(name, positions, elements)
      matches.append(match)

    return matches

  @staticmethod
  def get_suffixes(prefix, osm_db):
    found_names = osm_db.find_names(prefix)
    suffixes = []
    for name in found_names:
      suffix = name[len(prefix):]
      suffixes.append((name, suffix))
      short_version = OSMNameMatcher.abbreviated(suffix)
      if short_version != suffix:
        suffixes.append((name, short_version))
    return suffixes

  @staticmethod
  def abbreviated(name):
    short_version = name
    for regex, repl in OSMNameMatcher.abbrevs:
      short_version = regex.sub(repl, short_version)
    return short_version
