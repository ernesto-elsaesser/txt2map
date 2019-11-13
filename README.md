# map2txt

## Approach
The Geoparser detects place names (toponyms) in a provided input text. The algorithm parses the text in three steps:

1. Tokenize the input text and find all name "anchors", which are text spans starting with a capital letter or number
2. Check if any anchor matches any commonly recognized toponyms
3. For every match, load everything within a bounding box around the matches coordinate from OSM

The output is a list of found names together with the linked OSM references. Definitions of "commonly recognized toponyms" and "everything" follow below (see Data). Note that loading data from OSM can take some time.

## Usage

The [Geoparser](parser.py) can be used directly within Python, or via the included webserver.

The [Web Server](server.py) listens on port 80 for POST requests with text as body. The server replies with the parsing results encoded as JSON.

Futher the repository contains a [Dockerfile](Dockerfile) with allows building and running the webserver as a Docker container.

## Data

For step 2 a local database of commonly recognized toponyms is used. The database is derived from the publicly available [GeoNames](http://www.geonames.org) dataset (see http://download.geonames.org/export/dump/). All entries of feature class 'A' and 'P' above a certain population limit are used. The script [update-geonames-db.py](update-geonames-db.py) can be used to generate/update the database.

In step 3 street-level data is dynamically loaded from [OSM](https://www.openstreetmap.org). Given a bounding around a recognized toponym in step 2, the data loader will load any node, way and relation that has a name within that bounding box, using a prepared [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template.

Both GeoNames and OSM data are stored in local SQLite databases. If data for a toponym is available already, the OSM can be skipped. The script [clear-cache.py](clear-cache.py) can be used to clear cached OSM responses.