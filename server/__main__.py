import sys
from flask import Flask, request
from .ui import UIServer
from .nlp import NLPServer

if sys.argv[1] == 'ui':
  print('Starting txt2map UI server ...')
  server = UIServer()
  port = 80
elif sys.argv[1] == 'nlp':
  print('Starting txt2map NLP server (this may take a while) ...')
  server = NLPServer()
  port = 81
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
  
