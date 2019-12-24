from geoparser import Gazetteer

gaz = Gazetteer()
#gaz.update_top_level()

# data can be loaded from http://download.geonames.org/export/dump/
#data_path = '../allCountries.txt'
#gaz.extract_large_entries(data_path)

gaz.update_defaults()
