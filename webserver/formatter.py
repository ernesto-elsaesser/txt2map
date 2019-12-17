

class ResponseFormatter:

  def doc_to_json(self, doc):
    return [self._context_to_dict(c, doc) for c in doc.local_contexts.values()]
    
  def _context_to_dict(self, context, doc):
    global_matches = [self._global_to_dict(t, doc) for t in context.global_toponyms]
    local_matches = [self._local_to_dict(t, context) for t in context.positions]
    path = [g.name for g in context.hierarchy]
    return {'global_matches': global_matches,
            'local_matches': local_matches,
            'path': path,
            'confidence': context.confidence}

  def _global_to_dict(self, toponym, doc):
    return {'name': toponym,
            'positions': doc.positions[toponym],
            'geoname_id': doc.geonames[toponym].id}

  def _local_to_dict(self, toponym, context):
    elements = context.osm_elements[toponym]
    urls = [e.url() for e in elements]
    return {'name': toponym,
            'positions': context.positions[toponym],
            'osm_elements': urls}

  def doc_to_text(self, doc):
    contexts = doc.local_contexts.values()
    contexts = sorted(contexts, key=lambda c: c.confidence, reverse=True)

    text = ''
    for context in contexts:
      path = ' > '.join(g.name for g in context.hierarchy)
      topos = ', '.join(context.global_toponyms)
      text += f'{path} ({topos} | c={context.confidence:.2f}):\n'
      for toponym, elements in context.osm_elements.items():
        count = len(elements)
        text += f'\t{toponym} ({count} elements)\n'
      text += '\n'
    return text.encode('utf-8')
