from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types


class GoogleCloudNL:

  def __init__(self):
    self.client = language.LanguageServiceClient()

  def annotate_ner_wik(self, doc):
    type_ = enums.Document.Type.PLAIN_TEXT
    api_doc = {'content': doc.text, 'type': type_, 'language': 'en'}
    enc = enums.EncodingType.UTF8
    response = self.client.analyze_entities(api_doc, encoding_type=enc)

    for entity in response.entities:
      if entity.type == enums.Entity.Type.LOCATION:
        group = 'loc'
      elif entity.type == enums.Entity.Type.PERSON:
        group = 'per'
      elif entity.type == enums.Entity.Type.ORGANIZATION:
        group = 'org'
      else:
        group = 'msc'
      name = entity.name
      wiki_url = None
      if 'wikipedia_url' in entity.metadata:
        wiki_url = entity.metadata['wikipedia_url']
      for mention in entity.mentions:
        if mention.type == enums.EntityMention.Type.PROPER:
          pos = mention.text.begin_offset
          phrase = mention.text.content
          doc.annotate('ner', pos, phrase, group, 'gcnl')
          if wiki_url != None:
            doc.annotate('wik', pos, phrase, group, wiki_url)
