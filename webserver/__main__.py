import os
import logging
from flask import Flask, request, jsonify
from geoparser import Geoparser
from .formatter import ResponseFormatter

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO, 
                    datefmt="%Y-%m-%d %H:%M:%S")

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

parser = Geoparser()
formatter = ResponseFormatter()
dirname = os.path.dirname(__file__)
with open(dirname + '/index.html', 'rb') as f:
  index_html = f.read()

@app.route('/', methods=["GET"])
def serve_form():
  return index_html

@app.route('/', methods=['POST'])
def parse_text():
  req_text = request.get_data(as_text=True)
  results = parser.parse(req_text)
  accept = request.headers['Accept']
  if 'text/plain' in accept:
    return formatter.results_to_text(results)
  else:
    out_json = formatter.results_to_json(results)
    return jsonify(out_json)

app.run(host='0.0.0.0', port=80)
