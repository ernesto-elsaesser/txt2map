import os
import logging
import re
import pylev
from .model import LocalLayer
from .geonames import GeoNamesCache

class Continent:
  def __init__(self, geoname):
    self.id = geoname.id
    self.toponyms = {}  # toponym > position
    self.countries = {}

class Country:
  def __init__(self, geoname, continent):
    self.id = geoname.id
    self.continent = continent
    self.toponyms = {}  # toponym > position
    self.adm1s = {}

class Admin1:
  def __init__(self, geoname, country):
    self.id = geoname.id
    self.country = country
    self.toponyms = {} # toponym > position


class ToponymResolver:

  def __init__(self, gns_cache, doc):
    self.gns_cache = gns_cache
    self.doc = doc
    self.continents = {}
    self.adm1s = []
    self.hierarchy_cache = {}

  def resolve(self):

    for d, positions in self.doc.demonyms.items():
      self.doc.selected_senses[d] = self.doc.default_senses[d]
      self._insert(d, positions)

    for t, positions in self.doc.gaz_toponyms.items():
      self.doc.selected_senses[t] = self.doc.default_senses[t]
      self._insert(t, positions)

    for t, positions in self.doc.ner_toponyms.items():
      if t in self.doc.gaz_toponyms:
        continue
      candidates = self._fetch_candidates(t)
      if candidates == None:
        continue
      default = candidates[0]
      self.doc.default_senses[t] = default
      self.doc.all_senses[t] = candidates[1:]
      self.doc.selected_senses[t] = default
      self._insert(t, positions)
      self._recognize_ancestors(default)

    unsupported = self._find_unsupported_gaz_toponyms()
    for t in unsupported:
      logging.info(f'Considering non-default senses for {t}')
      candidates = self._fetch_candidates(t)
      if candidates != None:
        self.doc.all_senses[t] = candidates[1:] # TODO: check if default is the same!

    self._disambiguate(max_rounds=5)

  def _insert(self, toponym, positions):
    geoname = self.doc.selected_senses[toponym]
    hierarchy = self._hierarchy(geoname)
    l0_geo = hierarchy[0]
    if l0_geo.id in self.continents:
      continent = self.continents[l0_geo.id]
    else:
      continent = Continent(l0_geo)
      self.continents[l0_geo.id] = continent
    if len(hierarchy) == 1:
      continent.toponyms[toponym] = positions
      return
    l1_geo = hierarchy[1]
    if l1_geo.id in continent.countries:
      country = continent.countries[l1_geo.id]
    else:
      country = Country(l1_geo, continent)
      continent.countries[l1_geo.id] = country
    if len(hierarchy) == 2:
      country.toponyms[toponym] = positions
      return
    l2_geo = hierarchy[2]
    if l2_geo.id in country.adm1s:
      adm1 = country.adm1s[l2_geo.id]
    else:
      adm1 = Admin1(l2_geo, country)
      country.adm1s[l2_geo.id] = adm1
      self.adm1s.append(adm1)
    adm1.toponyms[toponym] = positions

  def _fetch_candidates(self, toponym):
    search_results = self.gns_cache.search(toponym)
    if len(search_results) == 0:
      return None

    if len(search_results) == 1:
      return search_results

    sorted_results = sorted(search_results, key=lambda g: -g.population)
    default = sorted_results[0]
    candidates = sorted_results[1:9]

    api_choice = search_results[0]
    if self._similar(api_choice.name, toponym):
      if api_choice in candidates:
        candidates.remove(api_choice)
      candidates.insert(0, api_choice)

    return [default] + candidates

  def _recognize_ancestors(self, geoname):
    known_toponyms = list(self.doc.gaz_toponyms)
    known_toponyms += list(self.doc.ner_toponyms)
    known_toponyms += list(self.doc.anc_toponyms)
    hierarchy = self._hierarchy(geoname)
    for ancestor in hierarchy[:-1]:
      toponym = ancestor.name
      if ancestor.population >= 50000:
        continue
      overlaps = [t for t in known_toponyms if toponym in t]
      if len(overlaps) > 0:
        continue
      positions = []
      for match in re.finditer(toponym, self.doc.text):
        positions.append(match.start())
      if len(positions) > 0:
        logging.info(f'Found {toponym} as ancestor of {geoname}')
        self.doc.anc_toponyms[toponym] = positions
        self.doc.default_senses[toponym] = ancestor
        self.doc.selected_senses[toponym] = ancestor
        self._insert(toponym, positions)

  def _find_unsupported_gaz_toponyms(self):
    if len(self.adm1s) < 2:
      return []

    unsupported = []
    for adm1 in self.adm1s:
      s2 = len(adm1.toponyms)
      if s2 > 1:
        continue # has siblings
      country = adm1.country
      s1 = len(country.toponyms)
      continent = adm1.continent
      s0 = len(continent.toponyms)
      if s0 + s1 > 1:
        continue # has more than one ancestor
      if s0 + s1 == 1:
        if s1 == 1 and len(country.adm1s) == 1:
          continue # has exclusive ancestor
        if s0 == 1 and len(continent.countries) == 1:
          continue # has exclusive ancestor
      unsupported += list(adm1.toponym.keys())

    return unsupported

  def _disambiguate(self, max_rounds):
    changed = True
    rounds = 0
    while changed and rounds < max_rounds:
      rounds += 1
      changed = False
      for toponym in self.doc.other_senses:
        selection = self._select_heuristically(toponym)
        if selection != self.doc.selected_senses[toponym]:
          changed = True
        self.doc.selected_senses[toponym] = selection

  def _hierarchy(self, geoname):
    if geoname.id in self.hierarchy_cache:
      return self.hierarchy_cache[geoname.id]
    hierarchy = self.gns_cache.get_hierarchy(geoname.id)
    self.hierarchy_cache[geoname.id] = hierarchy
    return hierarchy

  def _select_heuristically(self, toponym):
    # TODO: first find alternatives that improve the tree, then select largest/highest
    candidates = self.doc.other_senses[toponym]
    for candidate in candidates:
      self._recognize_ancestors(candidate)
      # TODO: see if inserted into group
      evidence = self._evidence(toponym, alt_resolved)
      if evidence > most_evidence:
        logging.info(f'chose {candidate} over {current} for {toponym}')
        chosen = candidate
        most_evidence = evidence + 0.5 # penalty for lower ranks

    return chosen

  def _evidence(self, toponym, resolved):
    geoname = resolved[toponym]
    first = min(self.recognized[toponym])
    name = geoname.name
    acronyms = self._acronyms(name)
    hierarchy = self._hierarchy(geoname)
    (ancs, sibs) = self._find_ancestors_and_siblings(toponym, resolved)

    # most prominent heuristic
    score = 4 / len(hierarchy)

    # name similarity
    if name not in toponym and toponym not in acronyms:
      dist = pylev.levenshtein(toponym, name)
      score -= (dist ** 1.5) / 10

    # ontological similarity heuristic
    for positions in apos.values():
      preceeding = min(positions) < first + 50
      score += 1.5 if preceeding else 0.5
    for _ in spos:
      score += 1.0

    return score

  def _acronyms(self, name):
    parts = name.split(' ')
    letters = [p[0] for p in parts if len(p) > 0]
    a1 = ''.join(letters)
    a2 = '.'.join(letters) + '.'
    return [a1,a2]

  def _similar(self, name1, name2):
    return pylev.levenshtein(name1, name2) < 2

  def make_local_layers(self):

    for adm1 in self.adm1s:
      geonames = [self.doc.default_senses[t] for t in adm1.toponyms]
      cities = [g for g in geonames if g.is_city]

      if len(cities) > 0:
        base = max(cities, key=lambda c: c.population)
        anchor_points = cities
      else:
        base = min(geonames, key=lambda c: c.population)
        anchor_points = self._drill_down(base)
        if len(anchor_points) == 0:
          logging.info(f'no local anchor point for {adm1.toponyms}')
          continue

      layer = LocalLayer(base, adm1, anchor_points, geonames)
      self.doc.local_layers.append(layer)
    

  def _drill_down(self, geoname):
    hierarchy = self._hierarchy(geoname)

    if len(hierarchy) == 1 or geoname.fcl != 'A':
      return []

    name = geoname.name

    while True:

      children = self.gns_cache.get_children(geoname.id)

      if len(children) == 0:
        # if there's nothing below, assume we are already local
        logging.info(f'using {geoname} as local context')
        return [geoname]

      else:
        children = sorted(children, key=lambda g: g.population, reverse=True)
        similar_child = None
        for child in children:
          if child.name in name or name in child.name:
            if child.is_city:
              logging.info(f'using {child} as local context for {name}')
              return [child]
            similar_child = child
            break

        if similar_child != None:
          geoname = similar_child
          continue

      return []
