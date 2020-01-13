import sys
import os
import json
import spacy
from flask import Flask, request

print('Loading large model ...')
nlp_sm = spacy.load('en_core_web_sm', disable=['parser'])
nlp_lg = spacy.load('en_core_web_lg', disable=['parser'])

port = sys.argv[1]
app = Flask(__name__)


@app.route('/', methods=['POST'])
def post():
  req_text = request.get_data(as_text=True)
  ent_map = {'lg': {}, 'sm': {}}
  doc_sm = nlp_sm(req_text)
  for ent in doc_sm.ents:
    ent_map['lg'][ent.text] = ent.label_
  doc_lg = nlp_lg(req_text)
  for ent in doc_lg.ents:
    ent_map['sm'][ent.text] = ent.label_
  return json.dumps(ent_map)


print(f'spaCy NER server listening on port {port}')
app.run(host='0.0.0.0', port=port)
