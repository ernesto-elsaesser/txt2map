import requests
import csv
import json
import io

class OSMElement:

  type_names = ['node', 'way', 'relation']

  def __init__(self, type_id, id):
    self.type_id = type_id
    self.id = id
    self.type_name = self.type_names[type_id]
    self.reference = f'{self.type_name}/{id}'

  def __repr__(self):
    return self.reference

class OverpassAPI:

  @staticmethod
  def load_names_in_bounding_box(bbox, excluded_keys):
    exclusions = ''.join('[!"' + e + '"]' for e in excluded_keys)

    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name", "ref"; false)]; ('
    query += f'node["name"]{exclusions}({bbox}); '
    query += f'way["name"]{exclusions}({bbox}); '
    query += f'rel["name"]{exclusions}({bbox}); '
    query += f'way[!"name"]["ref"]({bbox}); '  # include highway names
    query += '); out qt;'
    
    response = OverpassAPI.post_query(query)
    # universal newlines mode
    csv_input = io.StringIO(response.text, newline=None)
    reader = csv.reader(csv_input, delimiter='\t')
    return reader

  @staticmethod
  def load_geometries(elements):
    query = '[out:json]; ('
    for e in elements:
      query += f'{e.type_name}({e.id}); '
    query += '); out ids bb;'
    response = OverpassAPI.post_query(query)
    data = response.json()
    return data['elements']
    
  @staticmethod
  def post_query(query):
    url = 'http://overpass-api.de/api/interpreter'
    response = requests.post(url=url, data=query)
    response.encoding = 'utf-8'
    return response

