import logging
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
    self.osm_loader = OSMLoader(cache_dir, local_search_dist_km)

  def parse(self, text):
    doc = self.recognizer.parse(text)

    resolver = ToponymResolver(self.gns_cache, doc)
    resolver.resolve()
    resolver.make_local_layers()

    for context in doc.local_contexts:
      self.osm_loader.find_local_matches(context, doc)

      toponym_str = ', '.join(context.toponyms())
      logging.info('local toponyms: %s', toponym_str)

    self.assign_confidences(doc)
    logging.info('finished.')

    return doc

  def assign_confidences(self, doc):
    contexts = doc.local_contexts

    if len(contexts) == 0:
      return

    if len(contexts) == 1:
      vals = list(contexts.values())
      vals[0].confidence = 1.0
      return

    mention_counts = {}
    match_counts = {}
    population_counts = {}
    for key, context in contexts.items():
      mentions = 0
      for toponym in context.global_toponyms:
        mentions += doc.mention_count(toponym)
      mention_counts[key] = mentions
      match_counts[key] = len(context.positions)
      population_counts[key] = context.hierarchy[-1].population

      if len(context.global_toponyms) > 1:
        context.confidence += 0.2
      if len(context.positions) > 1:
        context.confidence += 0.2

    most_global_mentions = max(contexts, key=lambda k: mention_counts[k])
    if mention_counts[most_global_mentions] > 1:
      contexts[most_global_mentions].confidence += 0.3

    most_local_matches = max(contexts, key=lambda k: match_counts[k])
    if match_counts[most_local_matches] > 1:
      contexts[most_local_matches].confidence += 0.2

    biggest_population = max(contexts, key=lambda k: population_counts[k])
    contexts[biggest_population].confidence += 0.1
