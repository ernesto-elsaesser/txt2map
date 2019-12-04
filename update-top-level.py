import json
from geoparser import GeoNamesAPI

names = {}

def insert_names(geoname):
  print(geoname.name)
  detailed = GeoNamesAPI.get_geoname(geoname.id)
  names[detailed.name] = geoname.id
  names[detailed.asciiname] = geoname.id
  for entry in detailed.altnames:
    if 'lang' in entry and entry['lang'] == 'en' and entry['name'] != geoname.name:
      names[entry['name']] = geoname.id

continents = GeoNamesAPI.get_children(6295630) # Earth
for continent in continents:
  insert_names(continent)
  countries = GeoNamesAPI.get_children(continent.id)
  for country in countries:
    insert_names(country)

names['U.S.'] = 6252001
json_dict = json.dumps(names)

with open('geoparser/top-level.json', 'w') as f:
  f.write(json_dict)
