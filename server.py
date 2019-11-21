import http.server
import json
import logging
import parser
import osm

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
parser = parser.Geoparser()

class PostHandler(http.server.BaseHTTPRequestHandler):

  def log_message(self, format, *args):
    pass # disable default logging

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    with open('data/index.html', 'rb') as f:
      self.wfile.write(f.read())
    self.close_connection = True

  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    req_data = self.rfile.read(content_length)
    req_text = req_data.decode('utf-8')
    results = parser.parse(req_text)

    accept = self.headers['Accept']
    if 'text/plain' in accept:
      res_data = self.results_to_text(results)
    else:
      res_data = self.results_to_json(results)

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(res_data)
    self.close_connection = True

  def results_to_json(self, clusters):
    cluster_json = list(map(self.cluster_to_dict, clusters))
    return json.dumps(cluster_json, indent=2).encode('utf-8')

  def cluster_to_dict(self, cluster):
    geoname_matches = list(map(self.geoname_match_to_dict, cluster.matches))
    geoname_ancestors = list(map(self.geoname_match_to_dict, cluster.hierarchy))
    osm_matches = list(map(self.osm_match_to_dict, cluster.local_matches))
    return {'geoname_matches': geoname_matches,
            'geoname_ancestors': geoname_ancestors,
            'osm_matches': osm_matches,
            'confidence': cluster.confidence}

  def geoname_match_to_dict(self, match):
    return {'name': match.name,
            'positions': match.positions,
            'geoname_id': match.geoname.id}

  def osm_match_to_dict(self, match):
    return {'name': match.name,
            'positions': match.positions,
            'osm_elements': self.osm_element_urls(match)}

  def results_to_text(self, clusters):
    text = ''
    for cluster in clusters:
      path = cluster.description()
      text += f'{path} (c={cluster.confidence:.2f}):\n'
      for match in cluster.local_matches:
        count = len(match.positions)
        text += f'\t{match.name} ({count}x)\n'
        for url in self.osm_element_urls(match):
          text += f'\t\t{url}\n'
      text += '\n'
    return text.encode('utf-8')

  def osm_element_urls(self, match):
    return [e.url() for e in match.elements]


server = http.server.HTTPServer(('', 80), PostHandler)
logging.info('map2txt server running on port 80')
try:
  server.serve_forever()
except KeyboardInterrupt:
  pass
server.server_close()


