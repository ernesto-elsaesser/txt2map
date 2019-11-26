import logging
from .server import WebServer

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO, 
                    datefmt="%Y-%m-%d %H:%M:%S")

server = WebServer()
server.run()
