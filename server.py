import http.server
import json
import logging
import parser

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
parser = parser.Geoparser()
osm_url = 'https://www.openstreetmap.org'

class PostHandler(http.server.BaseHTTPRequestHandler):

  def log_message(self, format, *args):
    pass # disable default logging

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    with open('index.html', 'rb') as f:
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
    matches_json = list(map(self.match_to_dict, cluster.matches))
    return {'context': cluster.context_path(), 
            'confidence': cluster.confidence, 
            'matches': matches_json}

  def match_to_dict(self, match):
    return {'name': match.name,
            'positions': match.positions,
            'osm_elements': self.ref_urls(match)}

  def results_to_text(self, clusters):
    text = ''
    for cluster in clusters:
      path = cluster.path()
      text += f'{path} (c={cluster.confidence:.2f}):\n'
      for match in cluster.matches:
        count = len(match.positions)
        text += f'\t{match.name} ({count}x)\n'
        for url in self.ref_urls(match):
          text += f'\t\t{url}\n'
      text += '\n'
    return text.encode('utf-8')

  def ref_urls(self, match):
    urls = []
    for ref in match.refs[0]:
      urls.append(f'{osm_url}/node/{ref}')
    for ref in match.refs[1]:
      urls.append(f'{osm_url}/way/{ref}')
    for ref in match.refs[2]:
      urls.append(f'{osm_url}/relation/{ref}')
    return urls


server = http.server.HTTPServer(('', 80), PostHandler)
logging.info('map2txt server running on port 80')
try:
  server.serve_forever()
except KeyboardInterrupt:
  pass
server.server_close()


