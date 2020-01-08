from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from geoparser import Document


class GoogleCloudNL:

  def __init__(self):
    self.client = language.LanguageServiceClient()

  def annotate(self, doc):
    text = doc.text()

    type_ = enums.Document.Type.PLAIN_TEXT
    api_doc = {'content': text, 'type': type_, 'language': 'en'}
    enc = enums.EncodingType.UTF8
    response = self.client.analyze_entities(api_doc, encoding_type=enc)

    for entity in response.entities:
      if entity.type == enums.Entity.Type.LOCATION:
        ner_group = 'loc'
      elif entity.type == enums.Entity.Type.PERSON:
        ner_group = 'per'
      elif entity.type == enums.Entity.Type.ORGANIZATION:
        ner_group = 'org'
      else:
        ner_group = 'msc'
      name = entity.name
      wiki_url = None
      if 'wikipedia_url' in entity.metadata:
        wiki_url = entity.metadata['wikipedia_url']
      for mention in entity.mentions:
        if mention.type == enums.EntityMention.Type.PROPER:
          pos = mention.text.begin_offset
          phrase = mention.text.content
          doc.annotate('ner', pos, phrase, ner_group, 'gcnl')
          if ner_group == 'loc':
            doc.annotate('rec', pos, phrase, 'ner', name)
            if wiki_url != None:
              doc.annotate('res', pos, phrase, 'wik', wiki_url)
