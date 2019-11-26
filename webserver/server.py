import logging
import http.server
from .handler import RequestHandler
from geoparser import Geoparser


class WebServer(http.server.HTTPServer):

  def __init__(self, address='', port=80):
    self.parser = Geoparser()
    super().__init__((address, port), RequestHandler)

  def run(self):
    logging.info('map2txt server running on port %i', self.server_port)
    try:
      self.serve_forever()
    except KeyboardInterrupt:
      pass
    self.server_close()
