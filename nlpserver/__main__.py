import os
from flask import Flask, request
from .nlp import SpacyNLP

print('Loading NLP models ...')
nlp = SpacyNLP()
app = Flask(__name__)


@app.route('/', methods=['POST'])
def parse_text():
  req_text = request.get_data(as_text=True)
  doc = nlp.annotate(req_text)
  return doc.export_json()


app.run(host='0.0.0.0', port=81)
