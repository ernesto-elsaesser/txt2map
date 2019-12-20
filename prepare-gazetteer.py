from geoparser import Gazetteer

gaz = Gazetteer()
gaz.load_top_level()

# data can be loaded from http://download.geonames.org/export/dump/
data_path = '../allCountries.txt'
#gaz.load_large_entries(data_path)

#gaz.generate_defaults()
