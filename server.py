import http.server
import json
import logging
from parser import Geoparser

class PostHandler(http.server.BaseHTTPRequestHandler):

  parser = Geoparser()
  osm_url = 'https://www.openstreetmap.org'

  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    req_data = self.rfile.read(content_length)
    req_text = req_data.decode('utf-8')
    results = self.parser.parse(req_text)
    res_json = self.results_to_json(results)
    res_data = json.dumps(res_json, indent=2).encode('utf-8')

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(res_data)

  def results_to_json(self, results):
    json = []
    for start, name, refs in results:
      nodes = self.inflate_ref_urls('node', refs[0])
      ways = self.inflate_ref_urls('way', refs[1])
      relations = self.inflate_ref_urls('relation', refs[2])
      json.append({'name': name, 'pos': start, 'elements': nodes + ways + relations})
    return json

  def inflate_ref_urls(self, type_name, refs):
    # NOTE: base URL can be dropped at some point
    return list(map(lambda r: f'{self.osm_url}/{type_name}/{r}', refs))


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

server = http.server.HTTPServer(('', 80), PostHandler)
logging.info('map2txt server running on port 80')
try:
  server.serve_forever()
except KeyboardInterrupt:
  pass
server.server_close()


