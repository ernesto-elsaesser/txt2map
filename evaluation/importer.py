import os
import csv
import json
import datetime
from io import StringIO
from lxml import etree
from annotation import Document
from .corpus import Corpus

class GeoWebNewsImporter:

  def import_documents(self, corpus):
    self.gns_count = 0
    self.raw_count = 0

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

    print(f'Imported {self.gns_count + self.raw_count} toponyms ({self.gns_count}/{self.raw_count}).')

  def _annotate_gold_coords(self, doc, path, meta_len):
    positions = {}
    phrases = {}
    coords = {}
    geoname_ids = {}
    categories = {}
    noun_mods = []

    with open(path, encoding='utf-8') as f:
      reader = csv.reader(f, delimiter='\t')
      for row in reader:
        tag_id = row[0]
        data = row[1].split(' ')

        if tag_id.startswith('T'):  # BRAT token
          key = tag_id
          categories[key] = data[0]
          positions[key] = int(data[1]) - meta_len
          phrases[key] = row[2]

        elif tag_id.startswith('#'):  # BRAT annotator note
          key = data[1]
          if ',' in row[2]:
            arr = row[2].split(',')
            coords[key] = [float(s.strip()) for s in arr]
          elif row[2] != 'N/A':
            geoname_ids[key] = int(row[2])

        elif tag_id.startswith('A'):  # BRAT annotation
          if data[0] == "Modifier_Type" and data[2] == "Noun":
            key = data[1]
            noun_mods.append(key)

    for key, pos in positions.items():
      phrase = phrases[key]
      category = categories[key]
      if category not in ["Literal", "Mixed", "Metonymic", "Literal_Modifier"]:
        continue
      if category == "Literal_Modifier" and key not in noun_mods:
        continue
      if key in geoname_ids:
        doc.annotate('gld', pos, phrase, 'gns', geoname_ids[key])
        self.gns_count += 1
      elif key in coords:
        doc.annotate('gld', pos, phrase, 'raw', coords[key])
        self.raw_count += 1
      else:
        assert False



class LGLImporter:

  def import_documents(self, corpus, exclude_geo):
    self.gns_count = 0
    self.non_count = 0
    self.skip_count = 0

    dirname = os.path.dirname(__file__)
    corpus_file = dirname + '/corpora/lgl.xml'
    tree = etree.parse(corpus_file)

    for article in tree.getroot():
      doc_id = article.get('docid')
      text = article.find('text').text

      gold_doc = Document(text)
      self._annotate_gold_coords(gold_doc, article, exclude_geo)
      if len(gold_doc.get_all('gld')) > 0:
        corpus.add_document(doc_id, gold_doc)
      
    print(f'Imported {self.gns_count + self.non_count} toponyms ({self.gns_count}/{self.non_count} - {self.skip_count}).')

  def _annotate_gold_coords(self, doc, article, exclude_geo):
    toponyms = article.find('toponyms')

    for toponym in toponyms:
      tag = toponym.find('gaztag')
      if exclude_geo and tag != None:
        self.skip_count += 1
        continue

      pos = int(toponym.find('start').text)
      phrase = toponym.find('phrase').text

      if tag == None:
        doc.annotate('gld', pos, phrase, 'non', '')
        self.non_count += 1
      else:
        geoname_id = tag.get('geonameid')
        doc.annotate('gld', pos, phrase, 'gns', geoname_id)
        self.gns_count += 1


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
        if len(arr) == 3:
          gold_doc.annotate('gld', pos, phrase, 'raw', arr[1:3])
        else:
          gold_doc.annotate('gld', pos, phrase, 'gns', arr[1])

      corpus.add_document(doc_id, gold_doc)
