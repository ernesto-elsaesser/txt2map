import os
from .recognizer import ToponymRecognizer
from .resolver import ToponymResolver
from .geonames import GeoNamesCache
from .osm import OSMLoader


class Geoparser:

  def __init__(self, use_large_model=True, local_search_dist_km=15, cache_dir='cache'):
    if not os.path.exists(cache_dir):
      os.mkdir(cache_dir)
    self.gns_cache = GeoNamesCache(cache_dir)
    self.recognizer = ToponymRecognizer(self.gns_cache, use_large_model)
    self.resolver = ToponymResolver(self.gns_cache)
    self.osm_loader = OSMLoader(cache_dir, local_search_dist_km)

  def parse(self, text):
    doc = self.recognizer.parse(text)
    self.resolver.resolve(doc)
    for layer in doc.local_layers:
      self.osm_loader.find_local_matches(layer, doc)
    self.assign_confidences(doc)
    return doc

  def assign_confidences(self, doc):
    layers = doc.local_layers

    if len(layers) == 0:
      return

    if len(layers) == 1:
      layers[0].confidence = 1.0
      return

    for layer in layers:
      if len(layer.global_toponyms) > 1:
        layer.confidence += 0.2
      if layer.mentions > 1:
        layer.confidence += 0.2

    most_global_mentions = max(layers, key=lambda l: l.mentions)
    if most_global_mentions.mentions > 1:
      most_global_mentions.confidence += 0.3

    most_local_matches = max(layers, key=lambda l: len(l.toponyms))
    if len(most_local_matches.toponyms) > 1:
      most_local_matches.confidence += 0.2

    biggest_population = max(layers, key=lambda l: l.base.population)
    biggest_population.confidence += 0.1
