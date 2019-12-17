import logging
import re

class NameMatcher:

  abbr = {
    'N': 'North',
    'E': 'East',
    'S': 'South',
    'W': 'West',
    'NE': 'Northeast',
    'SE': 'Southeast',
    'SW': 'Southwest',
    'NW': 'Northwest',
    'Mt.': 'Mount',
    'St.': 'Saint'
  }

  abbr_end = {
    'St': 'Street',
    'Ave': 'Avenue',
    'Blvd': 'Boulevard',
    'Fwy': 'Freeway',
    'Pkwy': 'Parkway',
    'Ln': 'Lane',
    'Rd': 'Road',
    'Dr': 'Drive',
    'Sq': 'Square'
  }

  def __init__(self, use_nums, use_stops, min_len, fuzzy):
    self.use_nums = use_nums
    self.use_stops = use_stops
    self.min_len = min_len
    self.fuzzy = fuzzy
    self.abbreviations = []
    for s, l in self.abbr.items():
      self.abbreviations.append((re.compile(l), s))
    for s, l in self.abbr_end.items():
      self.abbreviations.append((re.compile(l), s))

  def find_names(self, doc, lookup_prefix):
    text_len = len(doc.text)
    names = {}
    prev_match_end = 0
    suffixes_for_prefixes = {}

    for start, (prefix, is_num, is_stop) in doc.anchors.items():
      if is_num and not self.use_nums: continue
      if is_stop and not self.use_stops: continue
      if start < prev_match_end: continue

      if prefix in suffixes_for_prefixes:
        suffixes = suffixes_for_prefixes[prefix]
      else:
        suffixes = self.get_suffixes(prefix, lookup_prefix)
        suffixes_for_prefixes[prefix] = suffixes

      text_pos = start + len(prefix)
      longest_match = None
      one_off = []
      while text_pos < text_len and len(suffixes + one_off) > 0:
        next_char = doc.text[text_pos]
        trimmed_suffixes = []
        trimmed_one_off = []
        for name, suffix in one_off:
          if suffix == '':
            longest_match = name
          elif suffix[0].lower() == next_char.lower():
            trimmed_one_off.append((name, suffix[1:]))
        for name, suffix in suffixes:
          if suffix == '':
            longest_match = name
          elif suffix[0].lower() == next_char.lower():
            trimmed_suffixes.append((name, suffix[1:]))
          elif self.fuzzy and next_char != ' ' and len(suffix) > 1:
            trimmed_one_off.append((name, suffix))
            trimmed_one_off.append((name, suffix[1:]))
        suffixes = trimmed_suffixes
        one_off = trimmed_one_off
        text_pos += 1

      if longest_match != None:
        prev_match_end = start + len(longest_match)
        if longest_match not in names:
          names[longest_match] = []
        names[longest_match].append(start)

    return names

  def get_suffixes(self, prefix, lookup_prefix):
    found_names = lookup_prefix(prefix)
    suffixes = []
    for name in found_names:
      if len(name) < self.min_len:
        continue
      suffix = name[len(prefix):]
      suffixes.append((name, suffix))
      short_version = self.abbreviated(suffix)
      if short_version != suffix:
        suffixes.append((name, short_version))
    if prefix in self.abbr:
      long_prefix = self.abbr[prefix]
      found_names = lookup_prefix(long_prefix)
      for name in found_names:
        suffix = name[len(long_prefix):]
        suffixes.append((name, suffix))
    return suffixes

  def abbreviated(self, name):
    short_version = name
    for regex, repl in self.abbreviations:
      short_version = regex.sub(repl, short_version)
    return short_version
