from .gazetteer import Gazetteer
from .geonames import GeoNamesCache


class GeoNamesTree:

  continent_map = Gazetteer.continent_map()
  country_boxes = Gazetteer.country_boxes()

  def __init__(self, doc):
    self.root = TreeNode(None, None)
    self.adm1s = []
    gns_cache = GeoNamesCache()
    for a in doc.get_all('res'):
      geoname = gns_cache.get(a.data)
      key_path = self.key_path(geoname)
      node = self.root.get(key_path, True)
      node.add(a.phrase, geoname, a.pos)
      if len(key_path) == 3 and node not in self.adm1s:
        self.adm1s.append(node)

  def leafs(self):
    leafs = []
    for cont in self.root.children.values():
      if len(cont.children) == 0:
        leafs.append(cont)
      for country in cont.children.values():
        if len(country.children) == 0:
          leafs.append(country)
        for adm1 in country.children.values():
          leafs.append(adm1)
    return leafs

  def key_path(self, g):
    if g.is_continent:
      cont_name = g.name
    elif g.cc in self.continent_map:
      cont_name = self.continent_map[g.cc]
    else:
      cont_name = 'Nowhere'
      for name, box in self.country_boxes.items():
        if box[1] < g.lat < box[3] and box[0] < g.lon < box[2]:  # [w, s, e, n]
          cont_name = self.continent_map[name]
          break

    key_path = [cont_name]
    if g.cc != "-":
      key_path.append(g.cc)
      if g.adm1 != "-" and g.adm1 != "00":
        key_path.append(g.adm1)
    return key_path

  def find_unsupported_adm1s(self):
    if len(self.adm1s) < 2:
      return []

    unsupported = []
    for node in self.adm1s:
      support = [len(n.geonames) for n in node.iter()]
      if sum(support) > 2 or support[0] > 1:
        continue  # multiple support or siblings
      if support[2] == 1 and len(node.parent.parent.children) == 1:
        continue  # exclusive continent
      if support[1] == 1 and len(node.parent.children) == 1:
        continue  # exclusive country
      unsupported.append(node)

    return unsupported


class TreeNode:

  def __init__(self, key, parent):
    self.key = key
    self.parent = parent
    self.children = {}  # key: TreeNode
    self.geonames = {}  # phrase: GeoName
    self.positions = {}  # phrase: [pos]

  def __repr__(self):
    return self.key

  def get(self, key_path, create):
    if len(key_path) == 0:
      return self
    key = key_path[0]
    if key not in self.children:
      if create:
        child = TreeNode(key, self)
        self.children[key] = child
      else:
        return None
    else:
      child = self.children[key]
    return child.get(key_path[1:], create)

  def add(self, phrase, geoname, position):
    if phrase not in self.geonames:
      self.geonames[phrase] = geoname
      self.positions[phrase] = [position]
    else:
      self.positions[phrase].append(position)

  def iter(self):
    node = self
    while node.key != None:
      yield node
      node = node.parent