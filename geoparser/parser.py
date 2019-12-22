import os
from .recognizer import ToponymRecognizer
from .resolver import ToponymResolver
from .geonames import GeoNamesCache
from .osm import OSMLoader
from .gazetteer import Gazetteer


class Geoparser:

  def __init__(self, use_large_model=True, local_search_dist_km=15, cache_dir='cache'):
    if not os.path.exists(cache_dir):
      os.mkdir(cache_dir)
    self.gns_cache = GeoNamesCache(cache_dir)
    self.recognizer = ToponymRecognizer(self.gns_cache, use_large_model)
    self.resolver = ToponymResolver(self.gns_cache)
    self.osm_loader = OSMLoader(cache_dir, local_search_dist_km)

  def parse(self, text, keep_defaults=False):
    doc = self.recognizer.parse(text)
    self.resolver.resolve(doc, keep_defaults)

    clusters = self.resolver.annotate_clusters(doc)
    for cluster_key, geonames in clusters.items():
      self.osm_loader.annotate_local_names(geonames, doc, cluster_key)

    self._annotate_confidences(doc, clusters)
    return doc

  def _annotate_confidences(self, doc, clusters):
    clust_count = len(clusters)

    if clust_count == 0:
      return

    confidences = {}
    for cluster_key, anchors in clusters.items():
      clust_anns = doc.get('clu', cluster_key)
      match_anns = doc.get('res', cluster_key)
      confidence = 'high'

      if clust_count > 1 and len(clust_anns) == 1 and len(anchors) > 0:
        if anchors[0].population < Gazetteer.pop_limit and ' ' not in clust_anns[0].phrase:
          if len(match_anns) == 0:
            confidence = 'low'

      for a in clust_anns + match_anns:
        confidences[a.phrase] = confidence

    for a in doc.get('res'):
      confidence = confidences[a.phrase]
      doc.annotate('con', a.pos, a.phrase, confidence, '')
