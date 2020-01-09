import sys
import os
from flask import Flask, request
from .ui import UIServer
from .nlp import NLPServer

if sys.argv[1] == 'ui':
  print('Starting txt2map UI server ...')
  server = UIServer()
  port = 80
elif sys.argv[1] == 'spacy':
  print('Starting spaCy NLP server (might take some time) ...')
  server = NLPServer()
  port = 8001
elif sys.argv[1] == 'cogcomp':
  print('Starting CogComp NLP server (might take some time) ...')
  t2m_dir = os.path.dirname(__file__)[:-6]
  cc_dir = t2m_dir + 'nlptools/cogcomp'
  os.system(f'cd "{cc_dir}"; java -Xmx4g -classpath ".:lib/*:dist/*" CogCompServer 8002')
  exit(0)
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
  
