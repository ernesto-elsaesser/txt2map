import json
from geoparser import GeoNamesCache, GeoNamesAPI

cache = GeoNamesCache()
names = {}

def insert_names(geoname):
  print(geoname.name)
  detailed = GeoNamesAPI.get_geoname(geoname.id) # use API directly to get all names
  names[detailed.name] = geoname.id
  names[detailed.asciiname] = geoname.id
  for entry in detailed.altnames:
    if 'lang' in entry and entry['lang'] == 'en' and entry['name'] != geoname.name:
      names[entry['name']] = geoname.id


continents = cache.get_children(6295630) # Earth
for continent in continents:
  insert_names(continent)
  countries = cache.get_children(continent.id)
  for country in countries:
    insert_names(country)
    if country.id == '2635167': # United Kingdom
      united_countries = cache.get_children(country.id)
      for united_country in united_countries:
        insert_names(united_country)


names['U.S.'] = 6252001
names['US'] = 6252001
names['USA'] = 6252001
names['UAE'] = 290557
names['USSR'] = 8354411
names['Atlantic'] = 3373405
names['Atlantic Ocean'] = 3373405
names['Pacific'] = 2363254
names['Pacific Ocean'] = 2363254
names['Indian Ocean'] = 1545739
names['Arctic Ocean'] = 2960860
names['Southern Ocean'] = 4036776

json_dict = json.dumps(names)

with open('geoparser/top-level.json', 'w') as f:
  f.write(json_dict)
