import requests
import csv
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from .pipeline import Step
from .document import Layer

class NERException(Exception):
  pass

class EntityRecognizer(Step):

  key = None
  layers = [Layer.ner]

  def __init__(self, url=None):
    self.server_url = url

  def annotate(self, doc):
    if self.server_url == None:
      raise NERException('NER service not configured!')

    text = self._preprocess(doc.text)
    req_data = text.encode('utf-8')
    try:
      response = requests.post(url=self.server_url, data=req_data, timeout=15)
    except:
      raise NERException('NER service not running!')

    response.encoding = 'utf-8'
    entities = self._extract_annotations(response.text, doc)
    for pos, phrase, group in entities:
      doc.annotate(Layer.ner, pos, phrase, group)


  def _preprocess(self, text):
    return text

  def _extract_annotations(self, response_text, doc):
    return []


class SpacyEntityRecognizer(EntityRecognizer):

  key = 'spacy'
  label_map = {'GPE': 'loc', 'LOC': 'loc', 'FAC': 'loc', 'NORP': 'dem', 'ORG': 'org', 'PERSON': 'per',
               'LANGUAGE': 'msc', 'PRODUCT': 'msc', 'EVENT': 'msc', 'WORK_OF_ART': 'msc', 'LAW': 'msc'}

  def _extract_annotations(self, response_text, doc):
    entities = []
    rows = response_text.split('\n')
    for row in rows:
      columns = row.split('\t')
      if len(row) == 0:
        continue
      label = columns[2]
      if label not in self.label_map:
        continue
      (pos, phrase) = self._normalized_name(int(columns[0]), columns[1])
      group = self.label_map[label]
      entities.append((pos, phrase, group))
    return entities

  def _normalized_name(self, pos, name):
    if name.startswith('the ') or name.startswith('The '):
      name = name[4:]
      pos += 4
    if name.endswith('\n'):
      name = name[:-1]
    if name.endswith('\'s'):
      name = name[:-2]
    elif name.endswith('\''):
      name = name[:-1]
    return (pos, name)



class StanfordEntityRecognizer(EntityRecognizer):

  key = 'stanford'
  label_map = {'LOCATION': 'loc', 'ORGANIZATION': 'org', 'PERSON': 'per', 'MISC': 'msc'}

  def _extract_annotations(self, response_text, doc):
    rows = response_text.split('\n')
    for row in rows:
      columns = row.split('\t')
      if len(row) == 0:
        continue
      label = columns[0]
      pos = int(columns[1])
      end = int(columns[2])
      phrase = doc.text[pos:end]
      group = self.label_map[label]
      entities.append((pos, phrase, group))
    return entities



class CogCompEntityRecognizer(EntityRecognizer):

  key = 'cogcomp'

  def _preprocess(self, text):
    return text.replace('[', '{').replace(']', '}')

  def _extract_annotations(self, response_text, doc):

    l = len(text)
    cc_l = len(response_text)
    i = pos = 0
    ent_pos = ent_group = ent_phrase = None

    ticks = ['"','\'','`']

    while pos < l and i < cc_l:
      c = response_text[i]
      oc = text[pos]

      if c in ticks:
        i += 1
      elif oc in ticks:
        pos += 1
      elif c == '[':
        ent_pos = pos
        ent_phrase = ''
        if response_text[i+1] == 'M':
          ent_group = 'msc'
          i += 6
        else:
          ent_group = response_text[i+1:i+4].lower()
          i += 5
      elif c == ']':
        if ent_phrase.startswith('The ') or ent_phrase.startswith('the '):
          ent_phrase = ent_phrase[4:]
          ent_pos += 4
        entities.append((ent_pos, ent_phrase, ent_group))
        ent_pos = ent_group = ent_phrase = None
        i += 1
      elif oc == '\n' and c != '\n':
        pos += 1
      elif c == ' ' and oc != ' ':
        i += 1
      elif c == oc or (c == '{' and oc == '[') or (c == '}' and oc == ']'):
        if ent_phrase != None:
          ent_phrase += oc
        pos += 1
        i += 1
      else:
        assert False

    return entities



class GCNLEntityLinker(Step):

  key = 'gcnl'
  layers = [Layer.ner, Layer.wiki]

  def __init__(self):
    try:
      self.client = language.LanguageServiceClient()
    except:
      self.client = None

  def annotate(self, doc):
    if self.client == None:
      raise NERException('No Google Cloud API credentials provided!')

    type_ = enums.Document.Type.PLAIN_TEXT
    api_doc = {'content': doc.text, 'type': type_, 'language': 'en'}
    enc = enums.EncodingType.UTF8
    response = self.client.analyze_entities(api_doc, encoding_type=enc)
    byte_text = doc.text.encode('utf8')

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
          byte_pos = mention.text.begin_offset
          byte_substr = byte_text[:byte_pos]
          substr = byte_substr.decode('utf8')
          pos = len(substr)
          phrase = mention.text.content
          doc.annotate(Layer.ner, pos, phrase, group)
          if wiki_url != None:
            doc.annotate(Layer.wiki, pos, phrase, group, wiki_url)