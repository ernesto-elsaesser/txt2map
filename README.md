# map2txt

## Approach
The Geoparser detects place names (toponyms) in a provided input text. The algorithm parses the text in five steps:

1. Find any geographically relevant named entities using spaCy NLP
2. Find populated places with these names using the GeoNames API
3. Disambiguate the results using multiple heuristics
4. For the resolved GeoNames, load ALL named elements from OSM
5. Scan the text for any of the received names

The output is a list of geographical clusters, each with a list of GeoName and OSM matches as well as a confidence score. Note that loading data from OSM can take some time.

## Usage

The [Geoparser](geoparser/parser.py) can be used directly from Python code, or via the included web server.

The [Web Server](webserver/server.py) listens on port 80 for POST requests with text as body. The response is a JSON object. If the client sends an `Accept` header with MIME type `text/plain` the server will format the output as dense and human-readable plain text. For testing the server also provides a simple HTML form as response to GET requests on any path.

The repository also contains a [Dockerfile](Dockerfile) which can be used to build a Docker container that runs the web server.

## OSM Data

In step 4 street-level data is loaded from [OSM](https://www.openstreetmap.org). Given a the list of bounding boxes of a cluster found in step 3, the parser will load any element (nodes, ways and relations) within the clusters bounding boxes that has a name tag, using a prepared [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template. The code can be found in the [OSM Module](geoparser/osm.py).

Loaded OSM data is stored in local SQLite databases. If data for a cluster is cached, the OSM query - which is the bottleneck of the parser - can be skipped. To clear the OSM cache, simply delete the `osmcache` folder created in the working directory.