import sys
import os
from flask import Flask, request
from geoparser import Document, PipelineBuilder, NERException

port = sys.argv[1]

spacy_url = os.getenv('SPACY_URL')
if spacy_url == None:
  print('No spaCy NER server URL provided!')
cogcomp_url = os.getenv('COGCOMP_URL')
if cogcomp_url == None:
  print('No CogComp NER server URL provided!')
stanford_url = os.getenv('STANFORD_URL')
if stanford_url == None:
  print('No Stanford NER server URL provided!')
gc_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if gc_creds == None:
  print('No Google Cloud API credentials provided!')

builder = PipelineBuilder()
builder.spacy_url = spacy_url
builder.cogcomp_url = cogcomp_url
builder.stanford_url = stanford_url
spacy_pipe = builder.build('spacy')
cogcomp_pipe = builder.build('cogcomp')
stanford_pipe = builder.build('stanford')
gcnl_pipe = builder.build('gcnl')

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

@app.route('/stanford', methods=['POST'])
def post_stanford():
  return process(stanford_pipe)

@app.route('/gcnl', methods=['POST'])
def post_gcnl():
  return process(gcnl_pipe)

def process(pipe):
  req_text = request.get_data(as_text=True)
  doc = Document(text=req_text)
  try:
    pipe.annotate(doc)
    return doc.export_layers()
  except NERException as e:
    return str(e), 500


print(f'UI server listening on port {port}')
app.run(host='0.0.0.0', port=port)

