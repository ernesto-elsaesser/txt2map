import os

for filename in os.listdir('data'):
  if filename[:4] == 'osm_':
    os.remove('data/' + filename)
