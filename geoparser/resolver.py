import os
import logging
import math
import json
import sqlite3
from Levenshtein import _levenshtein
from .model import ResolvedToponym, ToponymCluster
from .geonames import GeoNamesCache, GeoNamesAPI

class ToponymResolver:

  def __init__(self, cache_dir):
    self.gns_cache = GeoNamesCache(cache_dir)

    dirname = os.path.dirname(__file__)
    top_level_file = dirname + '/top-level.json'
    with open(top_level_file, 'r') as f:
      json_dict = f.read()
    self.top_level = json.loads(json_dict)

  def resolve(self, tmap):
    logging.info('resolving ...')

    search_results = {}
    selected = {}
    for name in tmap.toponyms():
      if name in self.top_level:
        default = self.gns_cache.get(self.top_level[name])
      else:
        results = self.gns_cache.search(name)
        if len(results) == 0: continue
        search_results[name] = results
        default = results[0]
        if not self._similar(default.name, name):
          default = max(results, key=lambda g: g.population)
      selected[name] = default

    changed = True
    rounds = 0
    while changed and rounds < 3:
      rounds += 1
      heuristically_selected = {}
      changed = False
      for name in selected:
        if name not in search_results:
          heuristically_selected[name] = selected[name]
          continue
        results = search_results[name]
        geoname = self._chose_heuristically(name, results, tmap, selected)
        if geoname.id != selected[name].id:
          changed = True
        heuristically_selected[name] = geoname
      selected = heuristically_selected

    resolved_toponyms = []
    for name, geoname in selected.items():
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)

      if not geoname.is_city and len(hierarchy) > 2:
        results = search_results[name]
        city_hierarchy = self._find_city_ancestor(name, hierarchy, results)
        if city_hierarchy != None:
          hierarchy = city_hierarchy

      positions = tmap.positions(name)
      resolved = ResolvedToponym(name, positions, hierarchy)
      resolved_toponyms.append(resolved)

    return resolved_toponyms

  def _chose_heuristically(self, name, search_results, tmap, selected):
    present_ids = set()
    regions = set()
    for n, g in selected.items():
      if n == name: continue
      present_ids.add(g.id)
      if g.adm1 != '-':
        regions.add(g.region())

    first_pos = tmap.first(name)
    close_names = set(tmap.window(first_pos - 150, first_pos + 50))
    close_names.remove(name)
    close_ids = set(selected[n].id for n in close_names if n in selected)

    chosen = selected[name]
    hierarchy = self.gns_cache.get_hierarchy(chosen.id)
    most_evidence = self._evidence(name, chosen, hierarchy,
                                   close_ids, regions, present_ids)

    sorted_by_size = sorted(search_results, key=lambda c: c.population, reverse=True)
    if chosen in sorted_by_size:
      sorted_by_size.remove(chosen)

    treshold = 1.0
    for geoname in sorted_by_size[:10]:
      hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      evidence = self._evidence(name, geoname, hierarchy,
                             close_ids, regions, present_ids)
      if evidence > most_evidence + treshold:
        logging.info(f'chose {geoname} over {chosen} for {name}')
        chosen = geoname
        most_evidence = evidence

    return chosen

  def _evidence(self, name, geoname, hierarchy, close_ids, regions, present_ids):

    score = 4 / len(hierarchy)
    if name not in geoname.name and geoname.name not in name:
      score /= _levenshtein.distance(name, geoname.name) + 1

    for ancestor in hierarchy[:-1]:
      if ancestor.id in close_ids:
        score += 1.5
      elif ancestor.region() in regions:
        score += 1.0
      elif ancestor.id in present_ids:
        score += 0.5

    return score

  def _find_city_ancestor(self, name, hierarchy, search_results):
    cities = [g for g in search_results if g.is_city and self._similar(g.name, name)]
    cities = sorted(cities, key=lambda c: c.population, reverse=True)
    depth = len(hierarchy)
    anchor_id = hierarchy[-2].id
    for geoname in cities[:10]:
      city_hierarchy = self.gns_cache.get_hierarchy(geoname.id)
      city_depth = len(city_hierarchy)
      hierarchy_ids = [g.id for g in city_hierarchy]
      if city_depth >= depth and anchor_id in hierarchy_ids:
        logging.info(f'chose city {geoname} over non-city {hierarchy[-1]} for {name}')
        return city_hierarchy

    return None

  def _similar(self, name1, name2):
    dist = _levenshtein.distance(name1, name2)
    return dist / len(name1) < 0.25

  def cluster(self, resolved_toponyms):
    logging.info('clustering toponyms ...')

    seeds = list(sorted(resolved_toponyms, 
            key=lambda t: t.geoname.population, reverse=True))

    clusters = []
    bound_names = set()

    while len(seeds) > 0:
      seed = seeds.pop()
      bound_names.add(seed.name)

      # find all matches in the same ADM1 area
      connected = [seed]
      hierarchy_ids = [g.id for g in seed.hierarchy]
      g1 = seed.geoname
      for toponym in resolved_toponyms:
        if toponym.name in bound_names:
          continue
        g2 = toponym.geoname
        if g1.cc == g2.cc != '-' and g1.adm1 == g2.adm1 != '-':
          connected.append(toponym)
          bound_names.add(toponym.name)
          seeds.remove(toponym)
        elif g2.id in hierarchy_ids:
          connected.append(toponym)
          if toponym in seeds:
            seeds.remove(toponym)

      cities = [t for t in connected if t.geoname.is_city]

      if len(cities) > 0:
        anchor = max(cities, key=lambda c: c.geoname.population)
      else:
        anchor = min(connected, key=lambda c: c.geoname.population)
        child = self._get_single_child(anchor) # try to drill down
        if child != None:
          cities.append(child)

      cluster = ToponymCluster(connected, cities, anchor)
      clusters.append(cluster)

    return sorted(clusters, key=lambda c: c.mentions(), reverse=True)

  def _get_single_child(self, resolved):
    children = GeoNamesAPI.get_children(resolved.geoname.id)
    single_child = None

    while len(children) == 1:
      single_child = children[0]
      children = GeoNamesAPI.get_children(single_child.id)

    if single_child == None:
      return resolved if len(children) == 0 else None

    hierarchy = self.gns_cache.get_hierarchy(single_child.id)
    return ResolvedToponym(single_child.name, [], hierarchy)
