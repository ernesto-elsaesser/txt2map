import os
import csv
import json
import datetime
from io import StringIO
from lxml import etree
from geoparser import Document
from .store import DocumentStore

class GeoWebNewsImporter:

  non_topo_types = ["Non_Toponym", "Non_Lit_Expression", "Literal_Expression"]
  rec_only_types = ["Demonym", "Homonym", "Language"]

  def import_documents(self):
    dirname = os.path.dirname(__file__)
    corpus_dir = dirname + '/corpora/GeoWebNews'

    paths = os.listdir(corpus_dir)
    docs = [p.replace('.txt', '') for p in paths if p.endswith('.txt')]

    for doc_id in docs:
      text_path = f'{corpus_dir}/{doc_id}.txt'
      annotation_path = f'{corpus_dir}/{doc_id}.ann'

      with open(text_path, encoding='utf-8') as f:
        text = f.read()

      doc = Document(text)

      self._annotate_gold_coords(doc, annotation_path, False)
      DocumentStore.save_text('GeoWebNews', doc_id, text)
      DocumentStore.save_annotations('GeoWebNews', doc_id, 'gold', doc)

      doc.delete_layer('gld')
      self._annotate_gold_coords(doc, annotation_path, True)
      DocumentStore.save_annotations('GeoWebNews', doc_id, 'gold-incl-rec', doc)

  def _annotate_gold_coords(self, doc, path, incl_rec):
    incomplete = {}

    with open(path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT token
          ann_type = data[0]
          if ann_type in self.non_topo_types:
            continue
          if ann_type in self.rec_only_types and not incl_rec:
            continue
          pos = int(data[1])
          phrase = row[2]
          incomplete[tag_id] = (pos, phrase)

        elif tag_id.startswith('#'):  # BRAT annotator note
          tag_id = data[1]
          if tag_id not in incomplete:
              continue

          (pos, phrase) = incomplete[tag_id]
          if ',' in row[2]:
            coords = row[2].split(',')
            lat = float(coords[0].strip())
            lon = float(coords[1].strip())
            doc.annotate('gld', pos, phrase, 'raw', [lat, lon])
          elif row[2] != 'N/A':
            geoname_id = int(row[2])
            doc.annotate('gld', pos, phrase, 'gns', geoname_id)


class LGLImporter:

  def import_documents(self):
    dirname = os.path.dirname(__file__)
    corpus_file = dirname + '/corpora/lgl.xml'
    tree = etree.parse(corpus_file)

    for article in tree.getroot():
      doc_id = article.get('docid')
      text = article.find('text').text

      doc = Document(text)
      self._annotate_gold_coords(doc, article)
      DocumentStore.save_text('LGL', doc_id, text)
      DocumentStore.save_annotations('LGL', doc_id, 'gold', doc)

  def _annotate_gold_coords(self, doc, article):

    toponyms = article.find('toponyms')

    for toponym in toponyms:
      tag = toponym.find('gaztag')
      if tag == None:
        continue

      pos = int(toponym.find('start').text)
      phrase = toponym.find('phrase').text
      geoname_id = tag.get('geonameid')
      #lat = float(tag.find('lat').text)
      #lon = float(tag.find('lon').text)

      doc.annotate('gld', pos, phrase, 'gns', geoname_id)
