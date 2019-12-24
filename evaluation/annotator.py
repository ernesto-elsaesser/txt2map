import os
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from geoparser import Document, Geoparser


class Annotator:

  def __init__(self, parser_name, parse, update=False):
    self.parse = parse
    self.parser_name = parser_name
    self.update = update
    dirname = os.path.dirname(__file__)
    self.base_dir = f'{dirname}/results/{parser_name}'

  def annotated_doc(self, corpus_name, document_name, text):
    results_dir = f'{self.base_dir}/{corpus_name}'
    data_path = f'{results_dir}/{document_name}.json'
    if os.path.exists(data_path) and not self.update:
      doc = Document(text)
      doc.load_annotations(data_path)
    else:
      doc = self.parse(text)
      if not os.path.exists(results_dir):
        os.mkdir(results_dir)
      doc.save_annotations(data_path)
    return doc


class T2MAnnotator(Annotator):

  def __init__(self, update=False, keep_defaults=False):
    self.parser = Geoparser()
    self.keep_defaults = keep_defaults
    super().__init__('txt2map', self._parse, update=update)

  def annotated_doc(self, corpus_name, document_name, text):
    if self.keep_defaults:
      document_name = 'def-' + document_name
    return super().annotated_doc(corpus_name, document_name, text)

  def _parse(self, text):
    return self.parser.parse(text, self.keep_defaults)


class GCNLAnnotator(Annotator):

  def __init__(self, corpus_name):
    self.client = language.LanguageServiceClient()
    super().__init__(corpus_name, 'google', self._parse, False)

  def _parse(self, text):
    type_ = enums.Document.Type.PLAIN_TEXT
    api_doc = {'content': text, 'type': type_, 'language': 'en'}
    enc = enums.EncodingType.UTF8
    response = client.analyze_entities(api_doc, encoding_type=enc)

    doc = Document(text)
    for entity in response.entities:
      if entity.type != 'LOCATION':
        continue
      toponym = entity.name
      for mention in entity.mentions:
        if mention.type == 'PROPER':
          pos = mention.text.begin_offset
          phrase = mention.text.content
          doc.annotate('rec', pos, phrase, 'ner', toponym)
      if 'wikipedia_url' in entity.metadata:
        url = entity.metadata['wikipedia_url']
        (lat, lon) = self._wiki_coordinates(url)
        doc.annotate('res', pos, phrase, 'sel', phrase)

