import os
import json
import csv
import re
import spacy
from .model import Document
from .matcher import NameMatcher

class ToponymRecognizer:

  def __init__(self, gns_cache, use_large_model):
    self.gns_cache = gns_cache

    self.use_large_model = use_large_model
    self.nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
    if self.use_large_model:
      self.nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

    dirname = os.path.dirname(__file__)
    defaults_file = dirname + '/defaults.json'
    with open(defaults_file, 'r') as f:
      json_dict = f.read()
    self.defaults = json.loads(json_dict)

    self.demonyms = {}
    demonyms_file = dirname + '/demonyms.csv'
    with open(demonyms_file, 'r') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        toponym = row[0]
        demos = row[1].split(',')
        for demonym in demos:
          self.demonyms[demonym] = toponym

    self.lookup_tree = {}
    known_toponyms = list(self.defaults.keys()) + list(self.demonyms.keys())
    for toponym in known_toponyms:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

    self.matcher = NameMatcher(False, False, 2, False)

  def parse(self, text):
    doc = Document(text)

    spacy_doc = self.nlp_sm(text)
    self._add_name_tokens(spacy_doc, doc)

    results = self.matcher.find_names(doc, self._lookup_prefix)
    for phrase, completions in results.items():
      toponym = completions[0].db_name
      if toponym in self.demonyms:
        toponym = self.demonyms[toponym]
        doc.demonyms[phrase] = positions
      else:
        doc.gaz_toponyms[phrase] = positions
      geoname_id = self.defaults[toponym]
      geoname = self.gns_cache.get(geoname_id)
      positions = [c.start for c in completions]
      doc.default_senses[phrase] = geoname

    ents = spacy_doc.ents
    if self.use_large_model:
      ents += self.nlp_lg(text).ents

    self._add_ner_toponyms(ents, doc)
    return doc

  def _lookup_prefix(self, prefix):
    key = prefix[:2]
    if key not in self.lookup_tree:
      return []
    toponyms = self.lookup_tree[key]
    return [t for t in toponyms if t.startswith(prefix)]

  def _add_name_tokens(self, tokens, doc):
    for token in tokens:
      first = token.text[0]
      is_num = first.isdigit()
      is_title = first.isupper()
      if is_title or is_num:
        # "US" is considered a stopword ...
        is_stop = token.is_stop and not token.text == 'US'
        tupel = (token.idx, token.text, is_num, is_stop)
        doc.name_tokens.append(tupel)

  def _add_ner_toponyms(self, ents, doc):
    for ent in ents:
      if ent.label_ not in ['GPE', 'LOC']:
        continue

      start = ent.start_char
      name = ent.text
      if name.startswith('the ') or name.startswith('The '):
        name = name[4:]
        start += 4
      if name.endswith('\'s'):
        name = name[:-2]
      elif name.endswith('\''):
        name = name[:-1]

      if name not in doc.ner.toponyms:
        doc.ner_toponyms[name] = []

      for match in re.finditer(re.escape(name), doc.text):
        doc.ner_toponyms[name].append(match.start())
