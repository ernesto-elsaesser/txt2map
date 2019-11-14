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
    results = self.parser.parse(req_text)

    accept = self.headers['Accept']
    if 'text/plain' in accept:
      res_data = self.results_to_text(results)
    else:
      res_data = self.results_to_json(results)

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(res_data)

  def results_to_json(self, clusters):
    cluster_json = list(map(self.cluster_to_dict, clusters))
    return json.dumps(cluster_json, indent=2).encode('utf-8')

  def cluster_to_dict(self, cluster):
    matches_json = list(map(self.match_to_dict, cluster.matches))
    return {'context': cluster.context_path(), 'matches': matches_json}

  def match_to_dict(self, match):
    nodes = self.inflate_ref_urls('node', match.refs[0])
    ways = self.inflate_ref_urls('way', match.refs[1])
    relations = self.inflate_ref_urls('relation', match.refs[2])
    return {'name': match.name,
            'positions': match.positions,
            'osm_elements': nodes + ways + relations}

  def inflate_ref_urls(self, type_name, refs):
    # NOTE: base URL can probably be dropped
    return list(map(lambda r: f'https://www.openstreetmap.org/{type_name}/{r}', refs))

  def results_to_text(self, clusters):
    text = ''
    for cluster in clusters:
      text += cluster.context_path() + ':\n'
      for match in cluster.matches:
        count = len(match.positions)
        ref_str = str(match.refs)
        text += f'\t{match.name} ({count}x) - {ref_str}\n'
      text += '\n'
    return text.encode('utf-8')


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

server = http.server.HTTPServer(('', 80), PostHandler)
logging.info('map2txt server running on port 80')
try:
  server.serve_forever()
except KeyboardInterrupt:
  pass
server.server_close()


