import sys
import os
import json
import spacy
from flask import Flask, request

print('Loading large model ...')
nlp = spacy.load('en_core_web_lg', disable=['parser'])

port = sys.argv[1]
app = Flask(__name__)


@app.route('/', methods=['POST'])
def post():
  req_text = request.get_data(as_text=True)
  doc = nlp(req_text)
  ent_map = {}
  for ent in doc.ents:
    ent_map[ent.text] = ent.label_
  return json.dumps(ent_map)


print(f'spaCy NER server listening on port {port}')
app.run(host='0.0.0.0', port=port)
