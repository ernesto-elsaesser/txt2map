import http.server
import json
import logging
import parser

class PostHandler(http.server.BaseHTTPRequestHandler):

  parser = parser.Geoparser()

  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    req_data = self.rfile.read(content_length)
    req_text = req_data.decode('utf-8')
    matches = self.parser.parse(req_text)
    res_json = list(map(self.match_to_json, matches))
    res_data = json.dumps(res_json, indent=2).encode('utf-8')

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(res_data)

  def match_to_json(self, match):
    nodes = self.inflate_ref_urls('node', match.refs[0])
    ways = self.inflate_ref_urls('way', match.refs[1])
    relations = self.inflate_ref_urls('relation', match.refs[2])
    return {'name': match.name,
            'positions': match.positions,
            'elements': nodes + ways + relations,
            'context': match.context}

  def inflate_ref_urls(self, type_name, refs):
    # NOTE: base URL can probably be dropped
    return list(map(lambda r: f'https://www.openstreetmap.org/{type_name}/{r}', refs))


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

server = http.server.HTTPServer(('', 80), PostHandler)
logging.info('map2txt server running on port 80')
try:
  server.serve_forever()
except KeyboardInterrupt:
  pass
server.server_close()


