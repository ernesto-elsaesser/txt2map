from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types


class GoogleCloudNL:

  def __init__(self):
    self.client = language.LanguageServiceClient()

  def annotate(self, doc):
    text = doc.text()

    type_ = enums.Document.Type.PLAIN_TEXT
    api_doc = {'content': text, 'type': type_, 'language': 'en'}
    enc = enums.EncodingType.UTF8
    response = client.analyze_entities(api_doc, encoding_type=enc)

    doc = Document(text)
    for entity in response.entities:
      if entity.type == 'LOCATION':
        group = 'loc'
      elif entity.type == 'PERSON':
        group = 'per'
      else:
        group = 'ent'
      name = entity.name
      includes_proper = False
      for mention in entity.mentions:
        if mention.type == 'PROPER':
          pos = mention.text.begin_offset
          phrase = mention.text.content
          doc.annotate('ner', pos, phrase, group, name)
          includes_proper = True
      if includes_proper and 'wikipedia_url' in entity.metadata:
        url = entity.metadata['wikipedia_url']
        (lat, lon) = self._wiki_coordinates(url)
        doc.annotate('rec', pos, phrase, 'api', name)
        doc.annotate('res', pos, phrase, 'api', name)
