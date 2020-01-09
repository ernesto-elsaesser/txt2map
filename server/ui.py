import os
import requests
from annotation import Document, Pipeline


class UIServer:

  rec_group_names = {'ner': 'NER Tool', 'gaz': 'Global Gazetteer', 'anc': 'Ancestor Scan'}
  res_group_names = {'top': 'Global Gazetteer Default Sense', 'api': 'GeoNames Top Sense', 'anc': 'Ancestor Scan', 
                'heu': 'Ontological Similarity Heuristic', 'wik': 'Wikipedia Reference'}

  def __init__(self, ner_port):
    self.pipe = Pipeline.standard(ner_port=ner_port)
    dirname = os.path.dirname(__file__)
    with open(dirname + '/index.html', 'rb') as f:
      self.index_html = f.read()

  def get(self):
    return self.index_html

  def post(self, req_text):
    doc = Document(text=req_text)
    self.pipe.annotate(doc)
    return self.doc_to_html(doc)

  def doc_to_html(self, doc):
    rec_anns = doc.annotations_by_position('rec')

    text = doc.text
    i = 0
    l = len(text)
    html = ''
    while i < l:
      anns = doc.get(i)

      if len(anns) == 0:
        html += text[i]
        i += 1
        continue

      phrase = list(anns.values())[0].phrase
      urls = []
      rec_info = 'Not recognized'
      clust_info = 'Not clustered'

      for layer, a in anns.items():
        if layer == 'rec':
          rec_info = 'Recognized by ' + self.rec_group_names[a.group]
        if layer == 'wik':
          urls.append(f'<a title="Wikipedia" href="{a.data}">WIKI</a>')
        if layer == 'res':
          urls.append(f'<a title="GeoNames" href="https://www.geonames.org/{a.data}">GEO</a>')
        if layer == 'clu':
          clust_info = 'Cluster' + a.group[4:]
          cluster_key = a.group
        if layer.startswith('clu-'):
          clust_info = 'Cluster' + layer[4:]
          els = self._rank_osm_elements(a_res.data)
          for e in els:
            urls.append(f'<a title="OpenStreetMap ({e[0]})" href="https://www.openstreetmap.org/{e[0]}/{e[1]}">OSM</a>')

      repl = f'<span title="{rec_info}. {clust_info}.">{phrase}</span>'
      if len(urls) > 0:
        shown = urls[:3]
        ell = ''
        if len(urls) > 3:
          ell = ' ...'
        repl += ' [' + (' '.join(shown)) + ell + ']'
      html += repl
      i += len(phrase)

    return html

  def _rank_osm_elements(self, els):
    # first relation then node then way
    return sorted(els, key=lambda e: -len(e[0]))
