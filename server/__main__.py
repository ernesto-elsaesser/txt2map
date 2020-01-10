import sys
import os
from flask import Flask, request
from annotation import PipelineBuilder
from .ui import UIServer
from .spacy import SpacyServer

port = sys.argv[2]
  
if sys.argv[1] == 'ui-spacy':
  spacy_port = sys.argv[3]
  print(f'Starting UI on port {port} using spaCy NER server on port {spacy_port} ...')
  builder = PipelineBuilder(spacy_port=spacy_port)
  server = UIServer(builder.build('spacy'))
elif sys.argv[1] == 'ui-cogcomp':
  cogcomp_port = sys.argv[3]
  print(f'Starting UI on port {port} server using CogComp NER server on port {cogcomp_port} ...')
  builder = PipelineBuilder(cogcomp_port=cogcomp_port)
  server = UIServer(builder.build('cogcomp'))
elif sys.argv[1] == 'ui-gcnl':
  print(f'Starting UI on port {port} server using GCNL NER pipeline ...')
  builder = PipelineBuilder()
  server = UIServer(builder.build('gcnl'))
elif sys.argv[1] == 'spacy':
  print(f'Starting spaCy NER server on port {port} (loading models takes some time) ...')
  server = SpacyServer()
else:
  print('Invalid argument')
  exit(0)

app = Flask(__name__)

@app.route('/', methods=["GET"])
def get():
  return server.get()

@app.route('/', methods=['POST'])
def post():
  req_text = request.get_data(as_text=True)
  return server.post(req_text)


app.run(host='0.0.0.0', port=port)
