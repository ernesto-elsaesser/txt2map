import sys
import os
from flask import Flask, request
from annotation import Document, PipelineBuilder

port = sys.argv[1]
spacy_port = os.getenv('SPACY_PORT')
cogcomp_port = os.getenv('COGCOMP_PORT')

builder = PipelineBuilder(spacy_port=spacy_port, cogcomp_port=cogcomp_port)
spacy_pipe = builder.build('spacy')
cogcomp_pipe = builder.build('cogcomp')
gcnl_pipe = builder.build('gcnl')

dirname = os.path.dirname(__file__)
index_path = dirname + '/index.html'

app = Flask(__name__)


@app.route('/', methods=["GET"])
def get():
  with open(index_path, 'rb') as f:
    return f.read()

@app.route('/spacy', methods=['POST'])
def post_spacy():
  req_text = request.get_data(as_text=True)
  doc = Document(text=req_text)
  pipeline.annotate(doc)
  return doc.export_layers()

@app.route('/cogcomp', methods=['POST'])
def post_cogcomp():
  req_text = request.get_data(as_text=True)
  doc = Document(text=req_text)
  pipeline.annotate(doc)
  return doc.export_layers()

@app.route('/gcnl', methods=['POST'])
def post_gcnl():
  req_text = request.get_data(as_text=True)
  doc = Document(text=req_text)
  pipeline.annotate(doc)
  return doc.export_layers()


print(f'UI server listening on port {port}')
app.run(host='0.0.0.0', port=port)

