

class ResponseFormatter:

  def doc_to_json(self, doc):
    return [self._layer_to_dict(l, doc) for l in doc.local_layers]
    
  def _layer_to_dict(self, layer, doc):
    global_matches = [self._global_to_dict(t, doc) for t in layer.global_toponyms]
    local_matches = [self._local_to_dict(t, layer) for t in layer.toponyms]
    return {'global_matches': global_matches,
            'local_matches': local_matches,
            'path': layer.path(),
            'confidence': layer.confidence}

  def _global_to_dict(self, toponym, doc):
    return {'name': toponym,
            'positions': doc.positions(toponym),
            'geoname_id': doc.selected_senses(toponym).id}

  def _local_to_dict(self, toponym, layer):
    elements = layer.osm_elements[toponym]
    urls = [e.url() for e in elements]
    return {'name': toponym,
            'positions': layer.toponyms[toponym],
            'osm_elements': urls}

  def doc_to_text(self, doc):
    layers = sorted(doc.local_layers, key=lambda l: -l.confidence)

    text = ''
    for l in layers:
      path = ' > '.join(l.path())
      topos = ', '.join(l.global_toponyms.keys())
      text += f'{path} ({topos} | c={l.confidence:.2f}):\n'
      for toponym, elements in l.osm_elements.items():
        count = len(elements)
        text += f'\t{toponym} ({count} elements)\n'
      text += '\n'
    return text.encode('utf-8')
