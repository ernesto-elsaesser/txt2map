import http.server
import json
import os

class RequestHandler(http.server.BaseHTTPRequestHandler):

  def log_message(self, format, *args):
    pass # disable default logging

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    dirname = os.path.dirname(__file__)
    with open(dirname + '/index.html', 'rb') as f:
      self.wfile.write(f.read())
    self.close_connection = True

  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    req_data = self.rfile.read(content_length)
    req_text = req_data.decode('utf-8')
    results = self.server.parser.parse(req_text)

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
    geoname_matches = list(map(self.toponym_to_dict, cluster.toponyms))
    osm_matches = list(map(self.osm_match_to_dict, cluster.local_matches))
    return {'geoname_matches': geoname_matches,
            'osm_matches': osm_matches,
            'path': cluster.path,
            'confidence': cluster.confidence}

  def toponym_to_dict(self, toponym):
    return {'name': toponym.name,
            'positions': toponym.positions,
            'geoname_id': toponym.selected.geoname.id}

  def osm_match_to_dict(self, match):
    return {'name': match.name,
            'positions': match.positions,
            'osm_elements': self.osm_element_urls(match)}

  def results_to_text(self, clusters):
    text = ''
    for cluster in clusters:
      text += f'{cluster} (c={cluster.confidence:.2f}):\n'
      for match in cluster.local_matches:
        count = len(match.positions)
        text += f'\t{match.name} ({count}x)\n'
        for url in self.osm_element_urls(match):
          text += f'\t\t{url}\n'
      text += '\n'
    return text.encode('utf-8')

  def osm_element_urls(self, match):
    return [e.url() for e in match.elements]
