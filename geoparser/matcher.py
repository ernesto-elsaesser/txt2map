import re
from unidecode import unidecode


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

  def __init__(self):
    self.starts = re.compile('\\b[A-Z0-9]')
    self.abbreviations = []
    for s, l in self.abbr.items():
      self.abbreviations.append((re.compile(l), s))
    for s, l in self.abbr_end.items():
      self.abbreviations.append((re.compile(l), s))

  def find_matches(self, doc, lookup_prefix, commit_match):
    text = doc.text + ' '  # allow matching of last token
    text_len = len(text)

    prev_end = 0
    saved = {}

    for m in self.starts.finditer(doc.text):
      start = m.start()
      if start < prev_end:
        continue

      prefix = text[start:start+4].split(' ')[0]

      if prefix in saved:
        completions = [c.clone(start) for c in saved[prefix]]
      else:
        completions = self._get_completions(prefix, lookup_prefix, start)
        saved[prefix] = completions

      text_pos = start + len(prefix)
      prev_end = text_pos
      longest_compl = None
      while text_pos < text_len and len(completions) > 0:
        next_char = text[text_pos]
        for c in completions:
          complete = c.trim(next_char)
          if complete:
            longest_compl = c
        completions = [c for c in completions if c.active]
        text_pos += 1

      if longest_compl != None:
        if commit_match(longest_compl):
          prev_end = longest_compl.end

  def _get_completions(self, prefix, lookup_prefix, pos):
    found_names = lookup_prefix(prefix)
    completions = []
    for db_name in found_names:
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
    elif prefix.isupper() and len(prefix) > 2:
      prefix_title = prefix[0] + prefix[1:].lower()
      found_names = lookup_prefix(prefix_title)
      for db_name in found_names:
        phrase = db_name.upper()
        upper_compl = Completion(phrase, prefix, db_name, pos)
        completions.append(upper_compl)
    return completions


class Completion:

  def __init__(self, phrase, prefix, lookup_phrase, pos):
    self.phrase = phrase
    self.prefix = prefix
    self.lookup_phrase = lookup_phrase
    self.pos = pos

    self.suffix = phrase[len(prefix):]
    self.match = prefix
    self.end = None
    self.active = True

  def __repr__(self):
    return self.suffix if self.active else self.match

  def clone(self, pos):
    return Completion(self.phrase, self.prefix, self.lookup_phrase, pos)

  def trim(self, char):

    if self.suffix == '':
      self.active = False
      if char.isupper() or char.islower():
        return False  # end in middle of token
      else:
        self.end = self.pos + len(self.match)
        return True

    n = self.suffix[0]
    nu = n.upper()
    accepted = [n, nu]
    asc = unidecode(n)
    if len(asc) == 1:
      accepted.append(asc)
      accepted.append(asc.upper())

    if char in accepted:
      self.suffix = self.suffix[1:]
      self.match += char
      return False

    else:
      self.active = False
      return False
