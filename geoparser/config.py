
class Config:

  cache_dir = 'cache'
  gazetteer_population_limit = 100_000
  gazetteer_class_prio = ['P', 'A', 'L', 'T']
  recog_large_ner_model = True
  resol_max_disam_rounds = 5
  local_search_dist = 15 # km
  local_match_min_len = 4
  local_match_fuzzy = True
  local_osm_exclusions = ['shop', 'power', 'office', 'cuisine']
