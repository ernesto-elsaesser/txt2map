

class ResponseFormatter:

  def results_to_json(self, clusters):
    return [self._cluster_to_dict(c) for c in clusters]
    
  def _cluster_to_dict(self, cluster):
    geoname_matches = [self._toponym_to_dict(t) for t in cluster.toponyms]
    osm_matches = [self._osm_match_to_dict(m) for m in cluster.local_matches]
    return {'geoname_matches': geoname_matches,
            'osm_matches': osm_matches,
            'path': cluster.path(),
            'confidence': cluster.confidence}

  def _toponym_to_dict(self, toponym):
    return {'name': toponym.name,
            'positions': toponym.positions,
            'geoname_id': toponym.geoname.id}

  def _osm_match_to_dict(self, match):
    return {'name': match.name,
            'positions': match.positions,
            'osm_elements': self._osm_element_urls(match)}

  def results_to_text(self, clusters):
    text = ''
    for cluster in clusters:
      text += f'{cluster} (c={cluster.confidence:.2f}):\n'
      for match in cluster.local_matches:
        count = len(match.positions)
        text += f'\t{match.name} ({count}x)\n'
        for url in self._osm_element_urls(match):
          text += f'\t\t{url}\n'
      text += '\n'
    return text.encode('utf-8')

  def _osm_element_urls(self, match):
    return [e.url() for e in match.elements]
