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

try:
  gcnl_pipe = builder.build('gcnl')
except:
  gcnl_pipe = None

dirname = os.path.dirname(__file__)
with open(dirname + '/index.html', 'rb') as f:
  index_html = f.read()

app = Flask(__name__)


@app.route('/', methods=["GET"])
def get():
  return index_html

@app.route('/spacy', methods=['POST'])
def post_spacy():
  return process(spacy_pipe)

@app.route('/cogcomp', methods=['POST'])
def post_cogcomp():
  return process(cogcomp_pipe)

@app.route('/gcnl', methods=['POST'])
def post_gcnl():
  if gcnl_pipe == None:
    return 'No Google Cloud API credentials provided!', 500
  return process(gcnl_pipe)

def process(pipe):
  req_text = request.get_data(as_text=True)
  doc = Document(text=req_text)
  try:
    pipe.annotate(doc)
    return doc.export_layers()
  except:
    return 'NER service not available!', 500


print(f'UI server listening on port {port}')
app.run(host='0.0.0.0', port=port)

