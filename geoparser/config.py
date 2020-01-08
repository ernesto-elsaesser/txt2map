
class Config:

  cache_dir = 'cache'
  gazetteer_population_limit = 100_000
  gazetteer_class_prio = ['P', 'A', 'L', 'T']
  resol_max_onto_sim_rounds = 5 # 0 to keep defaults
  local_search_dist = 15 # km
  local_match_min_len = 4
  local_osm_exclusions = ['shop', 'power', 'office', 'cuisine']
