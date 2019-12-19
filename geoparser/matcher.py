import logging
import re


class Completion:

  def __init__(self, phrase, prefix, db_name, start):
    self.phrase = phrase
    self.prefix = prefix
    self.db_name = db_name
    self.start = start
    
    self.suffix = phrase[len(prefix):]
    self.match = prefix
    self.end = None
    self.is_fuzzy = False
    self.was_fuzzy = False
    self.active = True

  def __repr__(self):
    return self.suffix if self.active else self.match

  def clone(self, start):
    return Completion(self.phrase, self.prefix, self.db_name, start)

  def trim(self, char, fuzzy):

    if self.suffix == '':
      self.active = False
      self.end = self.start + len(self.match)
      return True

    if self.suffix[0].lower() == char.lower():
      self.suffix = self.suffix[1:]
      self.match += char
      if self.is_fuzzy:
        self.is_fuzzy = False
        self.was_fuzzy = True
      return False

    if self.is_fuzzy and self.suffix[1].lower() == char.lower():
      self.suffix = self.suffix[2:]
      self.match += char
      self.is_fuzzy = False
      self.was_fuzzy = True
      return False

    can_fuzzy = fuzzy and not self.was_fuzzy and not self.is_fuzzy and len(self.suffix) > 1
    if can_fuzzy and char != ' ':
      self.match += char
      self.is_fuzzy = True
      return False

    else:
      self.active = False
      return False
      


class NameMatcher:

  abbr = {
    'N': 'North',
    'N.': 'North',
    'E': 'East',
    'E.': 'East',
    'S': 'South',
    'S.': 'South',
    'W': 'West',
    'W.': 'West',
    'NE': 'Northeast',
    'SE': 'Southeast',
    'SW': 'Southwest',
    'NW': 'Northwest',
    'N.E.': 'Northeast',
    'S.E.': 'Southeast',
    'S.W.': 'Southwest',
    'N.W.': 'Northwest',
    'Mt': 'Mount',
    'Mt.': 'Mount',
    'St': 'Saint',
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
    completed = {}
    prev_match_end = 0
    saved = {}

    for start, prefix, is_num, is_stop in doc.name_tokens:
      if is_num and not self.use_nums: continue
      if is_stop and not self.use_stops: continue
      if start < prev_match_end: continue

      if prefix in saved:
        completions = [c.clone(start) for c in saved[prefix]]
      else:
        completions = self._get_completions(prefix, lookup_prefix, start)
        saved[prefix] = completions

      text_pos = start + len(prefix)
      longest_completion = None
      while text_pos < text_len and len(completions) > 0:
        next_char = doc.text[text_pos]
        for c in completions:
          complete = c.trim(next_char, self.fuzzy)
          if complete:
            longest_completion = c
        completions = [c for c in completions if c.active]
        text_pos += 1

      if longest_completion != None:
        compl = longest_completion
        prev_match_end = compl.end
        if compl.match not in completed:
          completed[compl.match] = []
        completed[compl.match].append(compl)

    return completed

  def _get_completions(self, prefix, lookup_prefix, start):
    found_names = lookup_prefix(prefix)
    completions = []
    for db_name in found_names:
      if len(db_name) < self.min_len:
        continue
      compl = Completion(db_name, prefix, db_name, start)
      completions.append(compl)
      for regex, repl in self.abbreviations:
        phrase = regex.sub(repl, db_name)
        if phrase != db_name and phrase.startswith(prefix):
          short_compl = Completion(phrase, prefix, db_name, start)
          completions.append(short_compl)
    if prefix in self.abbr:
      long_prefix = self.abbr[prefix]
      found_names = lookup_prefix(long_prefix)
      for db_name in found_names:
        phrase = db_name.replace(long_prefix, prefix)
        if ' ' not in phrase:
          continue
        long_compl = Completion(phrase, prefix, db_name, start)
        completions.append(long_compl)
    return completions

