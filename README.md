# txt2map

txt2map is a street level geoparser written in Python. Unlike other geoparsers, txt2map does not only detect well-known names of countries and cities, but also street names, points of interest, public institutions, restaurants, etc. The system is still work in progress, but you can try it out [here](http://34.247.167.219). 

## Approach

The txt2map geoparser recognizes place names (toponyms) in text documents and resolves them to [GeoNames](https://www.geonames.org) or [OpenStreetMap](https://www.openstreetmap.org) entities. The algorithm parses the text in five steps:

1. Recognize place names using a combination of NLP technology and gazetteer matching
2. Retrieve resolution candidates from GeoNames API
3. Disambiguate the results using multiple heuristics
4. For each cluster of resolved GeoName entries, load ALL named elements from OpenStreetMap
5. Scan the text for any of the received names

The output is a set of annotations, including layers for recognized names, linked GeoNames identifiers, matches local names and matches OSM references. These annotations can be visulaized using the included web server. Note that loading data from OSM for the first time might take some time. 

The thesis that presents the underlying algorithm will be published here are soon as it is through review.

## Usage

The [Geoparser](geoparser/parser.py) can be used directly as Python module, or via the included web application. The web application is a simple HTML form that accepts an input texts, parses it and vizualizes the generated annotations. The web application uses a dedicated server for the NLP tool (currently spaCy). To run the application your machine, first start the NLP server via

```
python3 -m server nlp
```

and then the UI server via

```
python3 -m server ui
```

or simply execute the [start-servers.sh](start-servers.sh) script (note that the NLP server starts quite slow). The UI server listens on port 80 and serves the input form on any path. To simplify distribution, the repository further includes a [Dockerfile](Dockerfile) which can be used to build a Docker container that hosts the web application.

## Evaluation

The repository includes an evaluation package that provides a framework for performance measurement and corpus evaluation. The package contains the two corpora used for evaluation in the thesis, [GeoWebNews](https://link.springer.com/article/10.1007/s10579-019-09475-3) and the [Local-Global Lexicon](https://ieeexplore.ieee.org/abstract/document/5447903) (both obtained from Milan Grittas [collection of geoparsing resources](https://github.com/milangritta/Pragmatic-Guide-to-Geoparsing-Evaluation)). The package further includes code to parse these corpora using txt2map and the Google Cloud Natural Language API (as baseline). The scripts run all documents through one of the parsers and then calculate precision, recall, F1-Score and Accurary@Xkm (the percentage of toponyms resolved within X km of the gold coordinate).

## OSM Data

The geoparser dynamically loads substantial amounts of data from OSM. For every detected local cluster (usually city names), the parser will load any OSM element - nodes, ways and relations - within a radius of ~15km that has a name tag (distance configurable). The data is cached in local SQLite databases to avoid redundant loads. The size of these databases ranges from a few KB to ~20MB per cluster depending on the urban density of the requested area. The system uses the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) to retrieve OSM data. The [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template can be found [here](geoparser/osm.py#L93).
