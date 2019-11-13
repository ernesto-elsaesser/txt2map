import http.server
import json
import logging
from parser import Geoparser
from model import Match

class PostHandler(http.server.BaseHTTPRequestHandler):

  parser = Geoparser()

  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    req_data = self.rfile.read(content_length)
    req_text = req_data.decode('utf-8')
    results = self.parser.parse(req_text)
    res_json = list(map(Match.to_json, results))
    res_data = json.dumps(res_json, indent=2).encode('utf-8')

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(res_data)


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

server = http.server.HTTPServer(('', 80), PostHandler)
logging.info('map2txt server running on port 80')
try:
  server.serve_forever()
except KeyboardInterrupt:
  pass
server.server_close()


