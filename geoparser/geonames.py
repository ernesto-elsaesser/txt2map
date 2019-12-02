import os
import requests
import json
from .model import GeoName

class GeoNamesAPI:

  @staticmethod
  def search(name):
    params = [('name_equals', name)]
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
