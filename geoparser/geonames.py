import os
import requests
import json

class GeoNamesAPI:

  @staticmethod
  def search(name, maxRows=10):
    params = [('name_equals', name), ('maxRows', maxRows)]
    return GeoNamesAPI.get_json('search', params)

  @staticmethod
  def get_hierarchy(id):
    params = [('geonameId', id)]
    return GeoNamesAPI.get_json('hierarchy', params)

  @staticmethod
  def get_geoname(id):
    params = [('geonameId', id)]
    return GeoNamesAPI.get_json('get', params)

  @staticmethod
  def get_json(endpoint, params):
    url = f'http://api.geonames.org/{endpoint}JSON?username=map2txt'
    for key, value in params:
      url += f'&{key}={value}'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return res.json()
