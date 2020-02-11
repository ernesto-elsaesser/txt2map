from geoparser import Datastore

continents = {}
countries = {}
us_states = {}
continent_map = {}

for continent in Datastore.get_children(6295630):  # Earth
  continents[continent.name] = continent.id
  print('loading countries in', continent.name)
  for country in Datastore.get_children(continent.id):
    continent_map[country.cc] = continent.name
    countries[country.name] = country.id
    if country.id == 6252001:  # US
      for us_state in Datastore.get_children(country.id):
        us_states[us_state.name] = us_state.id
    if country.id == 2635167:  # UK
      for uk_country in Datastore.get_children(country.id):
        continent_map[uk_country.cc] = continent.name
        countries[uk_country.name] = uk_country.id

# common abbreviations

continents['EU'] = 6255148

countries['America'] = 6252001
countries['U.S.'] = 6252001
countries['US'] = 6252001
countries['USA'] = 6252001

countries['Britain'] = 2635167
countries['U.K.'] = 2635167
countries['UK'] = 2635167

countries['UAE'] = 290557

Datastore.save_data('continents', continents)
Datastore.save_data('countries', countries)
Datastore.save_data('us_states', us_states)
Datastore.save_data('continent_map', continent_map)