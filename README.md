# txt2map

txt2map is a street level geoparser written in Python (3). Unlike most available geoparsers, a street level geoparser does not only detect well-known names of countries and cities, but also street names, points of interest, public institution, restaurants, etc. This geoparser is the result of a master thesis, which describes the system in detail and provides evaluation results. The thesis will be published here as soon as possible.

## Approach

The txt2map geoparser recognizes place names (toponyms) in text documents and resolves them to [GeoNames](https://www.geonames.org) or [OpenStreetMap](https://www.openstreetmap.org) entities. The algorithm parses the text in five steps:

1. Recognize place names using a combination of NLP technology and gazetteer matching
2. Retrieve resolution candidates from GeoNames API
3. Disambiguate the results using multiple heuristics
4. For each cluster of resolved GeoName entries, load ALL named elements from OpenStreetMap
5. Scan the text for any of the received names

The output is a set of annotations, including layers for recognized names, linked GeoNames identifiers, matches local names and matches OSM references. These annotations can be visulaized using the included web server. Note that loading data from OSM for the first time might take some time.

## Usage

The [Geoparser](geoparser/parser.py) can be used directly as Python module, or via the included web server.

The [Web Server](webserver/server.py) listens on port 80 for POST requests with text as body. The response is a JSON object containing all annotation layers produced throughout the geoparsing process. TO visualize the annotations, the HTML form server on port 80 via GET can be used.

The repository also contains a [Dockerfile](Dockerfile) which can be used to build a Docker container that runs the web server.

## Evaluation

The repository includes an evaluation package that provides a framework for performance measurement and corpus evaluation. The package contains the two corpora used for evaluation in the thesis, [GeoWebNews](https://link.springer.com/article/10.1007/s10579-019-09475-3) and the [Local-Global Lexicon](https://ieeexplore.ieee.org/abstract/document/5447903) (both obtained from Milan Grittas [collection of geoparsing resources](https://github.com/milangritta/Pragmatic-Guide-to-Geoparsing-Evaluation)). The package further includes code to geoparse the corpora using txt2map and the Google Cloud Natural Language API (used as baseline). The scripts run all documents through one of the parsers and then calculate precision, recall, F1-Score and Accurary@161km (how many toponyms were resolved within tolerance - distance variable).

## OSM Data

The geoparser dynamically loads larger amounts of data from OSM. For ever detected local cluster (usually city names), the parser will load any element (nodes, ways and relations) within a radius of ~15km (adjustable) that has a name tag. The data is cached in local SQLite databases to avoid redundant loads. The size of these databases ranges from a few KB to ~20MB depending on the urban density of the requested area. The system uses the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) to retrieve OSM data. The [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template can be found [here](geoparser/osm.py).
