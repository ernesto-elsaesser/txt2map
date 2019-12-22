

class ResponseFormatter:

  rec_group_map = {'gaz': 'Gazetteer', 'ner': 'NER', 'anc': 'Ancestor'}

  def doc_to_html(self, doc):

    html = doc.text
    seen = []
    for a in doc.get('rec'):
      if a.phrase in seen:
        continue
      seen.append(a.phrase)

      rec_groups = []
      for ar in doc.get('rec', pos=a.pos):
        if ar.group.startswith('cl'):
          group_name = 'Local Context'
        else:
          group_name = self.rec_group_map[ar.group]
        rec_groups.append(group_name)

      urls = []
      for ag in doc.get('res', 'sel', pos=a.pos):
        urls.append(f'<a title="GeoNames" href="{self._gns_url(ag)}">G</a>')
      for al in doc.get('res', pos=a.pos, exclude_groups=['api', 'def', 'sel']):
        idx = al.group[2]
        els = self._rank_osm_elements(al.data)
        for e in els:
          urls.append(f'<a title="OpenStreetMap ({e[0]})" href="{self._osm_url(e)}">{idx}</a>')

      title = ', '.join(rec_groups)
      repl = f'<span title="{title}">{a.phrase}</span>'
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
