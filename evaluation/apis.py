import requests
import json
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from geoparser import Document

class GoogleNLParser:

  def __init__(self):
    self.client = language.LanguageServiceClient()

  def parse(self, text):
    doc = Document(text)
    document = types.Document(
      content=text,
      language='en',
      type=enums.Document.Type.PLAIN_TEXT)

    response = client.analyze_entities(document=document)

    for entity in response.entities:
      if entity.type != 'LOCATION':
        continue
      phrase = entity.name
      for mention in entity.mentions:
        if mention.type == 'PROPER':
          pos = mention.begin_offset # TODO: map
          doc.annotate('rec', pos, phrase, 'ner', phrase)
      if 'wikipedia_url' in entity.metadata:
        url = entity.metadata['wikipedia_url']
        (lat, lon) = self._wiki_coordinates(url)
        doc.annotate('res', pos, phrase, 'sel', phrase)


class OpenCalaisParser:

  x-ag-access-token
  Content-Type text/raw
  outputFormat:xml/rdf?
  POST https://api-eit.refinitiv.com/permid/calais.
  res.json()


class DBpediaParser:

  def parse(self, text):
    doc = Document(text)

  curl - X GET "https://api.dbpedia-spotlight.org/en/annotate?text=I%20live%20on%20Zwinglistra%C3%9Fe%20in%20Berlin.%20It's%20the%20capital%20city%20of%20Germany." - H "accept: application/json"



