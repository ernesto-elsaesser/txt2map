# txt2map

txt2map is a street level geoparser written in Python. Unlike other geoparsers, txt2map does not only detect well-known names of countries and cities, but also street names, points of interest, public institutions, restaurants, etc. The system is still work in progress, but you can try it out [here](http://54.229.3.214). 

## Approach

The txt2map geoparser recognizes place names (toponyms) in text documents and resolves them to [GeoNames](https://www.geonames.org) or [OpenStreetMap](https://www.openstreetmap.org) entities. The algorithm parses the text in five steps:

1. Recognize place names using a combination of NLP technology and gazetteer matching
2. Retrieve resolution candidates from GeoNames API
3. Disambiguate the results using multiple heuristics
4. For each cluster of resolved GeoName entries, load ALL named elements from OpenStreetMap
5. Scan the text for any of the received names

The output is an annotated document with annotation layers for recognized names as well as GeoNames and OSM references. These annotations can be visulaized through the included UI server. 

The thesis that presents the underlying algorithm will be published here are soon as it is through review.


## Usage

The geoparsing system is modular. The central component is the UI server, which hosts the web frontend and runs the actual geoparser. 

For NER tagging - which is a required pre-processing step for geoparsing - the UI server can use different NER tools:

- [spaCy](https://spacy.io) hosted on a dedicated server
- the [Illinois NETagger](https://cogcomp.seas.upenn.edu/page/software_view/NETagger) hosted on a dedicated server
- the [Google Cloud Natural Language API](https://cloud.google.com/natural-language/)

The servers for spaCy and Illinois NET are located in the [ner-server](ner-server) directory. Illinois NET is part of the CogComp NLP suite and thus the server is called CogComp.

The UI server as well as the two stand-alone NER servers come with Dockerfiles ([UI](Dockerfile), [spaCy](ner-server/spacy/Dockerfile), [CogComp](ner-server/cogcomp/Dockerfile)) for simple distribution.

The components that the UI server uses internally are structured as Python modules and can be used directly from code. The `annotaton` module contains the basic document model used for annotation throughout the system as well as processing pipelines. The `geoparser` module contains the geoparsing logic (everything after the NER step). The `evaluation` module contains code for corpus evaluation (used for the thesis, see below). The `ui-server` contains the actual web server.

The `run-docker-xxx.sh` scripts in the root directory allow simple building and running of the three Docker containers.


## OSM Data

The geoparser dynamically loads substantial amounts of data from OSM. For every detected local cluster (usually city names), the parser will load any OSM element - nodes, ways and relations - within a radius of ~15km that has a name tag (distance configurable). The data is cached in local SQLite databases to avoid redundant loads. The size of these databases ranges from a few KB to ~20MB per cluster depending on the urban density of the requested area. Therefore the initial laod of a cluster can take some time. The system uses the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) to retrieve OSM data. The [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template can be found [here](geoparser/osm.py#L84). 


## Evaluation

The repository includes an evaluation package that provides a framework for corpus evaluation. The package contains the two corpora used for evaluation in the thesis, [GeoWebNews](https://link.springer.com/article/10.1007/s10579-019-09475-3) and the [Local-Global Lexicon](https://ieeexplore.ieee.org/abstract/document/5447903) (both obtained from Milan Gritta's [collection of geoparsing resources](https://github.com/milangritta/Pragmatic-Guide-to-Geoparsing-Evaluation)). The package further includes code to annotate these corpora using the different available pipelines and measure performance metrics (F1-score, resolution accurary).