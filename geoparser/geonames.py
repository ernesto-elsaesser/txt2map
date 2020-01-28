import requests
import unidecode


class GeoName:

  def __init__(self, data=None, row=None):
    if data != None:
      self.id = data['geonameId']
      self.name = data['name']
      self.population = data['population']
      self.lat = float(data['lat'])
      self.lon = float(data['lng'])
      self.fcl = '-' if 'fcl' not in data else data['fcl']
      self.fcode = '-' if 'fcode' not in data else data['fcode']
      self.cc = '-' if 'countryCode' not in data else data['countryCode']
      self.adm1 = '-' if 'adminCode1' not in data else data['adminCode1']
      self.toponym_name = data['toponymName']
      # not cached:
      if 'asciiName' in data:
        self.asciiname = data['asciiName']
      if 'alternateNames' in data:
        self.altnames = data['alternateNames']
      if 'wikipediaURL' in data:
        self.wiki_url = data['wikipediaURL']
      else:
        self.wiki_url = None
    else:
      self.id = row[0]
      self.name = row[1]
      self.population = row[2]
      self.lat = row[3]
      self.lon = row[4]
      self.fcl = row[5]
      self.fcode = row[6]
      self.cc = row[7]
      self.adm1 = row[8]
      self.toponym_name = row[9]

    self.is_city = self.fcl == 'P'
    self.is_admin = self.fcl == 'A'
    self.is_country = self.fcode.startswith('PCL')
    self.is_continent = self.fcode == 'CONT'
    self.is_ocean = self.fcode == 'OCN'

  def region(self):
    return f'{self.cc}-{self.adm1}'

  def char_match(self, name):
    a = self._base_name(name)
    b = self._base_name(self.name)
    c = self._base_name(self.toponym_name)
    return a == b or a == c

  def _base_name(self, toponym):
    toponym = toponym.rstrip('.')
    try:
      toponym = unidecode(toponym)
    except:
      pass
    return toponym.lower()

  def __repr__(self):
    return f'{self.toponym_name}, {self.adm1}, {self.cc} [{self.fcode}]'


class GeoNamesAPI:

  @staticmethod
  def search(name, feature_classes):
    params = [('q', name)]
    for fcl in feature_classes:
      params.append(('featureClass', fcl))
    json_data = GeoNamesAPI.get_json('search', params)
    if not 'geonames' in json_data:
      return []
    json_array = json_data['geonames']
    return list(map(GeoName, json_array))

  @staticmethod
  def get_hierarchy(id):
    params = [('geonameId', id)]
    json_data = GeoNamesAPI.get_json('hierarchy', params)
    json_array = json_data['geonames']
    return list(map(GeoName, json_array))

  @staticmethod
  def get_children(id):
    params = [('geonameId', id)]
    json_data = GeoNamesAPI.get_json('children', params)
    if not 'geonames' in json_data:
      return []
    json_array = json_data['geonames']
    return list(map(GeoName, json_array))

  @staticmethod
  def get_geoname(id):
    params = [('geonameId', id)]
    json_data = GeoNamesAPI.get_json('get', params)
    return GeoName(json_data)

  @staticmethod
  def get_json(endpoint, params):
    url = f'http://api.geonames.org/{endpoint}JSON?username=map2txt'
    for key, value in params:
      url += f'&{key}={value}'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return res.json()
