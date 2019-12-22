import re


class Completion:

  def __init__(self, phrase, prefix, db_name, pos):
    self.phrase = phrase
    self.prefix = prefix
    self.db_name = db_name
    self.pos = pos
    
    self.suffix = phrase[len(prefix):]
    self.match = prefix
    self.end = None
    self.is_fuzzy = False
    self.was_fuzzy = False
    self.active = True

  def __repr__(self):
    return self.suffix if self.active else self.match

  def clone(self, pos):
    return Completion(self.phrase, self.prefix, self.db_name, pos)

  def trim(self, char, fuzzy):

    if self.suffix == '':
      self.active = False
      self.end = self.pos + len(self.match)
      return True

    accepted = [char, char.lower()]
    if self.suffix[0] in accepted:
      self.suffix = self.suffix[1:]
      self.match += char
      if self.is_fuzzy:
        self.is_fuzzy = False
        self.was_fuzzy = True
      return False

    if self.is_fuzzy and self.suffix[1] in accepted:
      self.suffix = self.suffix[2:]
      self.match += char
      self.is_fuzzy = False
      self.was_fuzzy = True
      return False

    if fuzzy and not self.was_fuzzy and not self.is_fuzzy and char != ' ' \
      and len(self.suffix) > 1 and len(self.match + self.suffix) > 8:
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

  def __init__(self, ignore, min_len, fuzzy):
    self.ignore = ignore
    self.min_len = min_len
    self.fuzzy = fuzzy
    self.abbreviations = []
    for s, l in self.abbr.items():
      self.abbreviations.append((re.compile(l), s))
    for s, l in self.abbr_end.items():
      self.abbreviations.append((re.compile(l), s))

  def recognize_names(self, doc, group, lookup_prefix):
    text_len = len(doc.text)
    prev_match_end = 0
    saved = {}

    for a in doc.get('tok', exclude_groups=self.ignore):
      if a.pos < prev_match_end: continue

      if a.phrase in saved:
        completions = [c.clone(a.pos) for c in saved[a.phrase]]
      else:
        completions = self._get_completions(a.phrase, lookup_prefix, a.pos)
        saved[a.phrase] = completions

      text_pos = a.pos + len(a.phrase)
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
        c = longest_completion
        prev_match_end = c.end
        doc.annotate('rec', a.pos, c.match, group, c.db_name)

  def _get_completions(self, prefix, lookup_prefix, pos):
    found_names = lookup_prefix(prefix)
    completions = []
    for db_name in found_names:
      if len(db_name) < self.min_len:
        continue
      compl = Completion(db_name, prefix, db_name, pos)
      completions.append(compl)
      for regex, repl in self.abbreviations:
        phrase = regex.sub(repl, db_name)
        if phrase != db_name and phrase.startswith(prefix):
          short_compl = Completion(phrase, prefix, db_name, pos)
          completions.append(short_compl)
    if prefix in self.abbr:
      long_prefix = self.abbr[prefix]
      found_names = lookup_prefix(long_prefix)
      for db_name in found_names:
        phrase = db_name.replace(long_prefix, prefix)
        if ' ' not in phrase:
          continue
        long_compl = Completion(phrase, prefix, db_name, pos)
        completions.append(long_compl)
    return completions

