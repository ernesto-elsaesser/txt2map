import os
from .matcher import NameMatcher
from .gazetteer import Gazetteer
from .recognizer import GazetteerRecognizer
from .resolver import GeoNamesResolver
from .osm import OSMLoader
from .config import Config


class Geoparser:

  def __init__(self):
    cache_dir = Config.cache_dir
    if not os.path.exists(cache_dir):
      os.mkdir(cache_dir)

    self.gaz = Gazetteer()
    self.resolver = GeoNamesResolver(self.gaz)
    self.osm_loader = OSMLoader()

  def annotate(self, doc):
    self.resolver.annotate(doc)
    clusters = self.resolver.annotate_clusters(doc)
    for cluster_key, geonames in clusters.items():
      if len(geonames) > 0:
        self.osm_loader.annotate_local_names(geonames, doc, cluster_key)
    self._annotate_con(doc, clusters)

  def _annotate_con(self, doc, clusters):
    clust_count = len(clusters)

    if clust_count == 0:
      return

    confidences = {}
    for cluster_key, anchors in clusters.items():
      clust_anns = doc.get('clu', cluster_key)
      match_anns = doc.get('res', cluster_key)
      confidence = 'high'

      if clust_count > 1 and len(clust_anns) == 1 and len(anchors) > 0:
        a = clust_anns[0]
        in_gaz = a.phrase in self.gaz.defaults
        if not in_gaz and ' ' not in a.phrase:
          if len(match_anns) == 0:
            confidence = 'low'

      for a in clust_anns + match_anns:
        confidences[a.phrase] = confidence

    for a in doc.get('res'):
      confidence = confidences[a.phrase]
      doc.annotate('con', a.pos, a.phrase, confidence, '')
