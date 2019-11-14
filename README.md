# map2txt

## Approach
The Geoparser detects place names (toponyms) in a provided input text. The algorithm parses the text in four steps:

1. Parse the text for "anchors", which are text spans starting with a capital letter, using regular expressions
2. Check if any anchor matches any commonly recognized toponym from GeoNames
3. For every match, load all named elements within a bounding box around the toponyms coordinate from OSM
4. Check if any anchor matches any of the element names from OSM

The output is a list geographical contexts, each with a list of OSM matches. Note that loading data from OSM can take some time.

## Usage

The [Geoparser](parser.py) can be used directly from Python code, or via the included web server.

The [Web Server](server.py) listens on port 80 for POST requests with text as body. The server replies with the parsing results encoded as JSON. If the client sends an `Accept` header with MIME type `text/plain` the server will format the output as short and readable plain text.

To test the server, you can run the following curl command:

```
$ curl -H "Accept: text/plain" -d "Walking in Memphis, but do I really feel the way I feel? Saw the ghost of Elvis on Union Avenue." localhost:80
```

The repository also provides a [Dockerfile](Dockerfile) which can be used to build a Docker container that runs the web server.

## Data

For step 2 a local database of commonly recognized toponyms is used. The database is derived from the publicly available [GeoNames](http://www.geonames.org) data set (see http://download.geonames.org/export/dump/). The database contains all entries of feature class `A` and `P` above a certain population limit. The script [update-geonames-db.py](update-geonames-db.py) can be used to generate/update the database.

In step 3 street-level data is loaded from [OSM](https://www.openstreetmap.org). Given a bounding box around a toponym recognized in step 2, the data loader will load any element (nodes, ways and relations) within that bounding box that has a name tag, using a prepared [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) template.

Both GeoNames and OSM data is stored in local SQLite databases. If data for a bounding box is available already, the OSM query -- which is the bottleneck of the parser -- can be skipped. The script [clear-cache.py](clear-cache.py) can be used to clear cached OSM responses. This is useful when the application somehow created empty or corrupt databases which prevent correct parsing.