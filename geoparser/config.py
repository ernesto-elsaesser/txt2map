
class Config:

  cache_dir = 'cache'
  gazetteer_population_limit = 100_000
  geonames_search_classes = ['P', 'A', 'L', 'T', 'H', 'V']
  local_search_dist = 15 # km
  local_match_min_len = 4
  local_osm_exclusions = ['shop', 'power', 'office', 'cuisine']
