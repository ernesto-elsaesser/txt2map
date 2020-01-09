import os
import requests
from geoparser import GazetteerRecognizer, Geoparser, Document


class UIServer:

  rec_group_names = {'gaz': 'Global Gazetteer', 'ner': 'NER Tool', 'anc': 'Ancestor Scan'}
  res_group_names = {'top': 'Global Gazetteer Default Sense', 'api': 'GeoNames Top Sense', 'anc': 'Ancestor Scan', 
                'heu': 'Ontological Similarity Heuristic', 'wik': 'Wikipedia Reference'}

  def __init__(self):
    self.gazrec = GazetteerRecognizer()
    self.geoparser = Geoparser()
    dirname = os.path.dirname(__file__)
    with open(dirname + '/index.html', 'rb') as f:
      self.index_html = f.read()

  def get(self):
    return self.index_html

  def post(self, req_text):
    doc = Document(text=req_text)

    body = req_text.encode('utf-8')
    nlp_res = requests.post(url='http://localhost:8001', data=body)
    nlp_res.encoding = 'utf-8'
    doc.set_annotation_json(nlp_res.text)

    self.gazrec.annotate(doc)
    self.geoparser.annotate(doc)
    return self.doc_to_html(doc)

  def doc_to_html(self, doc):
    rec_anns = doc.annotations_by_position('rec')

    text = doc.text()
    i = 0
    l = len(text)
    html = ''
    while i < l:
      if i not in rec_anns:
        html += text[i]
        i += 1
        continue

      a_rec = rec_anns[i]

      if a_rec.group.startswith('cl'):
        source = 'Local Gazetteer'
      else:
        source = self.rec_group_names[a_rec.group]

      urls = []
      a_res = doc.get('res', pos=i)[0]
      if a_res.group.startswith('cl'):
        idx = a_res.group[2]
        els = self._rank_osm_elements(a_res.data)
        for e in els:
          urls.append(f'<a title="OpenStreetMap ({e[0]})" href="{self._osm_url(e)}">{idx}</a>')
      elif a_res.group == 'wik':
        urls.append(f'<a title="Wikipedia" href="{a.data}">W</a>')
      else:
        urls.append(f'<a title="GeoNames" href="{self._gns_url(a_res)}">G</a>')

      repl = f'<span title="Recognized by {source}">{a_rec.phrase}</span>'
      if len(urls) > 0:
        shown = urls[:3]
        ell = ''
        if len(urls) > 3:
          ell = ' ...'
        repl += ' [' + (' '.join(shown)) + ell + ']'
      html += repl
      i += len(a_rec.phrase)

    return html

  def _rank_osm_elements(self, els):
    # first relation then node then way
    return sorted(els, key=lambda e: -len(e[0]))

  def _gns_url(self, ann):
    return f'https://www.geonames.org/{ann.data}'

  def _osm_url(self, e):
    return f'https://www.openstreetmap.org/{e[0]}/{e[1]}'
