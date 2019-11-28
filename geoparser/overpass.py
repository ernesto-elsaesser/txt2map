import requests
import csv
import io

class OverpassAPI:

  @staticmethod
  def load_names_in_bounding_boxes(bounding_boxes):
    query = '[out:csv(::id, ::type, "name", "name:en", "alt_name", "short_name"; false)]; ('
    for bounding_box in bounding_boxes:
      bbox = ','.join(map(str, bounding_box))
      query += f'node["name"][!"shop"]({bbox}); way["name"]({bbox}); rel["name"]({bbox}); '
    query += '); out qt;'
    response = OverpassAPI.post_query(query)
    csv_input = io.StringIO(response.text, newline=None) # universal newlines mode
    reader = csv.reader(csv_input, delimiter='\t')
    return reader

  @staticmethod
  def load_geometries(elements):
    query = '[out:json]; ('
    for elem in elements:
      query += f'{elem.element_type}({elem.reference}); '
    query += '); out geom;'
    response = OverpassAPI.post_query(query)
    return response.json()
    
  @staticmethod
  def post_query(query):
    url = 'http://overpass-api.de/api/interpreter'
    response = requests.post(url=url, data=query)
    response.encoding = 'utf-8'
    return response
