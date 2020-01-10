import sys
import os
from flask import Flask, request
from annotation import Document, PipelineBuilder

port = sys.argv[1]

if sys.argv[2] == 'spacy':
  spacy_port = sys.argv[3]
  print(f'Starting UI server on port {port} using spaCy NER server on port {spacy_port} ...')
  builder = PipelineBuilder(spacy_port=spacy_port)
  pipeline = builder.build('spacy')
elif sys.argv[2] == 'cogcomp':
  cogcomp_port = sys.argv[3]
  print(f'Starting UI server on port {port} server using CogComp NER server on port {cogcomp_port} ...')
  builder = PipelineBuilder(cogcomp_port=cogcomp_port)
  pipeline = builder.build('cogcomp')
elif sys.argv[2] == 'gcnl':
  print(f'Starting UI server on port {port} server using GCNL NER pipeline ...')
  builder = PipelineBuilder()
  pipeline = builder.build('gcnl')
else:
  print('Invalid argument')
  exit(0)

app = Flask(__name__)

dirname = os.path.dirname(__file__)
index_path = dirname + '/index.html'


@app.route('/', methods=["GET"])
def get():
  with open(index_path, 'rb') as f:
    return f.read()

@app.route('/', methods=['POST'])
def post():
  req_text = request.get_data(as_text=True)
  doc = Document(text=req_text)
  pipeline.annotate(doc)
  return doc.export_layers()


app.run(host='0.0.0.0', port=port)

