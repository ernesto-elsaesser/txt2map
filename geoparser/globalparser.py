import re
from unidecode import unidecode
from .datastore import Datastore
from .document import Layer
from .pipeline import Step
from .matcher import NameMatcher
from .gazetteer import Gazetteer
from .admtree import GeoNamesTree
from .util import GeoUtil


class GlobalGeoparser(Step):

  layers = [Layer.gres]

  def __init__(self, keep_defaults=False):
    self.key = 'globaldef' if keep_defaults else 'global'
    self.keep_defaults = keep_defaults
    self.matcher = NameMatcher()

    self.top_level_topos = Gazetteer.top_level()
    self.lookup_tree = {}
    for toponym in self.top_level_topos:
      key = toponym[:2]
      if key not in self.lookup_tree:
        self.lookup_tree[key] = []
      self.lookup_tree[key].append(toponym)

    self.candidates = {}

  def annotate(self, doc):
    resolutions = {}

    for a in doc.get_all(Layer.topo):
      if a.phrase in resolutions:
        continue
      if a.phrase in self.top_level_topos:
        geoname_id = self.top_level_topos[a.phrase]
        default = Datastore.get_geoname(geoname_id)
      else:
        results = Datastore.search_geonames(a.phrase)
        if len(results) == 0:
          continue
        default = results[0]

      print(f'gres - chose {default} for "{a.phrase}"')
      resolutions[a.phrase] = default

    self._find_missed_top_levels(doc, resolutions)

    should_continue = not self.keep_defaults
    rounds = 0
    while should_continue:
      rounds += 1
      should_continue = False
      tree = GeoNamesTree(resolutions)

      for adm1 in tree.adm1s:
        if tree.adm1_supported(adm1):
          continue
        (toponym, geoname) = list(adm1.geonames.items())[0] # only one in node
        new = self._select_heuristically(toponym, geoname, tree)
        if new != None:
          should_continue = True
          resolutions[toponym] = new
          print(f'gres - heuristic preferred {new} for {toponym}')
          break
    
    for a in doc.get_all(Layer.topo):
      if a.phrase in resolutions:
        geoname = resolutions[a.phrase]
        data = [geoname.lat, geoname.lon, geoname.id]
        doc.annotate(Layer.gres, a.pos, a.phrase, 'global', data)

  def _find_missed_top_levels(self, doc, resolutions):
    topo_indices = doc.annotations_by_index(Layer.topo)

    def lookup(prefix):
      key = prefix[:2]
      if key not in self.lookup_tree:
        return []
      toponyms = self.lookup_tree[key]
      return [t for t in toponyms if t.startswith(prefix)]

    def commit(c):
      indices = range(c.pos, c.end)
      overlaps = [i for i in topo_indices if i in indices]
      if len(overlaps) > 0:
        return False
      geoname_id = self.top_level_topos[c.lookup_phrase]
      resolutions[c.match] = Datastore.get_geoname(geoname_id)
      return True

    self.matcher.find_matches(doc, lookup, commit)

  def _select_heuristically(self, toponym, current, tree):
    results = Datastore.search_geonames(toponym)

    parts = len(toponym.split(' '))

    candidates = []
    for g in results:
      if g.id == current.id:
        continue
      g_parts = len(g.name.split(' '))
      if g_parts > parts and g.population == 0:
        continue
      candidates.append(g)

    if len(candidates) == 0:
      return None

    candidates = sorted(candidates, key=lambda g: -g.population)

    for g in candidates[:10]:
      node = tree.node_for(g, False)
      if node != None and toponym not in node.geonames:
        return g

    return None
