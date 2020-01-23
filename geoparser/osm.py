import requests
import csv
import json
import io


class OverpassAPI:

  @staticmethod
  def load_names_in_bounding_boxes(bounding_boxes, excluded_keys):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name", "ref"; false)]; ('
    exclusions = ''.join('[!"' + e + '"]' for e in excluded_keys)
    for bounding_box in bounding_boxes:
      bbox = ','.join(map(str, bounding_box))
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
      query += f'{e[0]}({e[1]}); '
    query += '); out geom;'
    response = OverpassAPI.post_query(query)
    return response.json()
    
  @staticmethod
  def post_query(query):
    url = 'http://overpass-api.de/api/interpreter'
    response = requests.post(url=url, data=query)
    response.encoding = 'utf-8'
    return response

