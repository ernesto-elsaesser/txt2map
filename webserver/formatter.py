

class ResponseFormatter:

  def doc_to_html(self, doc):

    html = doc.text
    seen = []
    for a in doc.get('rec'):
      if a.phrase in seen:
        continue
      seen.append(a.phrase)

      urls = []

      for a in doc.get('res', 'sel', pos=a.pos):
        urls.append(f'<a title="GeoNames" href="{self._gns_url(a)}">G</a>')
        
      for a in doc.get('res', pos=a.pos, exclude_groups=['api', 'def', 'sel']):
        idx = a.group[2]
        els = self._rank_osm_elements(a.data)
        for e in els:
          urls.append(f'<a title="OpenStreetMap ({e[0]})" href="{self._osm_url(e)}">{idx}</a>')

      repl = f'<span title="{a.group}">{a.phrase}</span>'
      if len(urls) > 0:
        shown = urls[:3]
        ell = ''
        if len(urls) > 3:
          ell = ' ...'
        repl += ' [' + (' '.join(shown)) + ell + ']'
      html = html.replace(a.phrase, repl)

    return html
    
  def _rank_osm_elements(self, els):
    # first relation then node then way
    return sorted(els, key=lambda e: -len(e[0]))

  def _gns_url(self, ann):
    return f'https://www.geonames.org/{ann.data}'

  def _osm_url(self, e):
    return f'https://www.openstreetmap.org/{e[0]}/{e[1]}'
