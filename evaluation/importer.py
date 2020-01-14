import os
import csv
import json
import datetime
from io import StringIO
from lxml import etree
from annotation import Document
from .corpus import Corpus

class GeoWebNewsImporter:

  non_topo_types = ["Non_Toponym", "Non_Lit_Expression", "Literal_Expression"]
  rec_only_types = ["Demonym", "Homonym", "Language"]

  def import_documents(self, corpus):
    dirname = os.path.dirname(__file__)
    corpus_dir = dirname + '/corpora/GeoWebNews'

    paths = os.listdir(corpus_dir)
    docs = [p.replace('.txt', '') for p in paths if p.endswith('.txt')]

    for doc_id in docs:
      text_path = f'{corpus_dir}/{doc_id}.txt'
      annotation_path = f'{corpus_dir}/{doc_id}.ann'

      with open(text_path, encoding='utf-8') as f:
        meta = next(f)
        meta_len = len(meta)
        text = f.read()

      gold_doc = Document(text)
      self._annotate_gold_coords(gold_doc, annotation_path, meta_len)
      corpus.add_document(doc_id, gold_doc)

  def _annotate_gold_coords(self, doc, path, meta_len):
    res_tags = {}

    with open(path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT token
          ann_type = data[0]
          if ann_type in self.non_topo_types:
            continue
          pos = int(data[1]) - meta_len
          phrase = row[2]
          doc.annotate('rec', pos, phrase, 'gld', phrase)

          if ann_type not in self.rec_only_types:
            res_tags[tag_id] = (pos, phrase)

        elif tag_id.startswith('#'):  # BRAT annotator note
          tag_id = data[1]
          if tag_id not in res_tags:
              continue

          (pos, phrase) = res_tags[tag_id]
          if ',' in row[2]:
            coords = row[2].split(',')
            lat = float(coords[0].strip())
            lon = float(coords[1].strip())
            doc.annotate('res', pos, phrase, 'raw', [lat, lon])
          elif row[2] != 'N/A':
            geoname_id = int(row[2])
            doc.annotate('res', pos, phrase, 'gns', geoname_id)


class LGLImporter:

  def import_documents(self, corpus, exclude_geo):
    dirname = os.path.dirname(__file__)
    corpus_file = dirname + '/corpora/lgl.xml'
    tree = etree.parse(corpus_file)

    for article in tree.getroot():
      doc_id = article.get('docid')
      text = article.find('text').text

      gold_doc = Document(text)
      self._annotate_gold_coords(gold_doc, article, exclude_geo)
      if len(gold_doc.get_all('rec')) > 0:
        corpus.add_document(doc_id, gold_doc)

  def _annotate_gold_coords(self, doc, article, exclude_geo):
    toponyms = article.find('toponyms')

    for toponym in toponyms:
      pos = int(toponym.find('start').text)
      phrase = toponym.find('phrase').text
      tag = toponym.find('gaztag')

      if tag != None and exclude_geo:
        continue

      doc.annotate('rec', pos, phrase, 'gld', phrase)

      if tag != None:
        geoname_id = tag.get('geonameid')
        #lat = float(tag.find('lat').text)
        #lon = float(tag.find('lon').text)
        doc.annotate('res', pos, phrase, 'gns', geoname_id)


class TestsImporter:

  def import_documents(self, corpus):
    dirname = os.path.dirname(__file__)
    json_path = f'{dirname}/corpora/tests.json'
    with open(json_path, encoding='utf-8') as f:
      tests = json.load(f)

    for doc_id, data in tests.items():
      text = data['text']
      anns = data['anns']

      gold_doc = Document(text)
      for arr in anns:
        phrase = arr[0]
        pos = text.find(phrase)
        gold_doc.annotate('rec', pos, phrase, 'gld', phrase)
        if len(arr) == 3:
          gold_doc.annotate('res', pos, phrase, 'raw', arr[1:3])
        else:
          gold_doc.annotate('res', pos, phrase, 'gns', arr[1])

      corpus.add_document(doc_id, gold_doc)
