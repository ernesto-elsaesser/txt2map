# map2txt

## Approach
The Geoparser detects place names (toponyms) in a provided input text. The algorithm parses the text in five steps:

1. Find any geographically relevant named entities using spaCy NLP
2. Find populated places with these names using GeoNames data
3. Disambiguate the results using a clustering algorithm based on geopolitical hierarchies
3. For the best fitting name clusters, load ALL named elements from OSM
4. Scan the text for the received names

The output is a list of geographical clusters, each with a list of OSM matches and a confidence score. Note that loading data from OSM can take some time.

## Usage

The [Geoparser](parser.py) can be used directly from Python code, or via the included web server.

The [Web Server](server.py) listens on port 80 for POST requests with text as body. The response is a JSON object. If the client sends an `Accept` header with MIME type `text/plain` the server will format the output as dense and human-readable plain text. For manual use the server also provides a simple HTML form (as response to GET requests on any path).

The repository also contains a [Dockerfile](Dockerfile) which can be used to build a Docker container that runs the web server.

## Data

For step 2 a local database of city names is used. The database is derived from the publicly available [GeoNames](http://www.geonames.org) data set using the [update-geonames-db.py](update-geonames-db.py) script.

In step 4 street-level data is loaded from [OSM](https://www.openstreetmap.org). Given a the list of bounding boxes of a cluster found in step 3, the data loader will load any element (nodes, ways and relations) within these bounding boxes that has a name tag, using a prepared [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template.

Both GeoNames and OSM data is stored in local SQLite databases. If data for a cluster is available already, the OSM query - which is the bottleneck of the parser - can be skipped. The script [clear-cache.py](clear-cache.py) can be used to clear cached OSM responses.