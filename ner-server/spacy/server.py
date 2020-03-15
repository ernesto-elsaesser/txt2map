import sys
import os
import json
import spacy
from flask import Flask, request

print('Loading large model ...', flush=True)
nlp = spacy.load('en_core_web_lg', disable=['parser'])

port = sys.argv[1]
app = Flask(__name__)


@app.route('/', methods=['POST'])
def post():
  req_text = request.get_data(as_text=True)
  spacy_doc = nlp(req_text)
  lines = ''
  for ent in spacy_doc.ents:
    lines += f'{ent.start_char}\t{ent.text}\t{ent.label_}\n'
  return lines


print(f'spaCy NER server listening on port {port}')
app.run(host='0.0.0.0', port=port)
