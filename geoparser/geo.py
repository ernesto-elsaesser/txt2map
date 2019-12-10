import geojson_utils
from osm2geojson import json2geojson
from .model import OSMElement

class GeoUtil:

  @staticmethod
  def make_point(lat, lng):
      return {'type': 'Point', 'coordinates': [lng, lat]}

  @staticmethod
  def bounding_box(lat, lng, corner_dist):
    start = GeoUtil.make_point(lat, lng)
    ne = geojson_utils.destination_point(start, 45, corner_dist)
    n = ne['coordinates'][1]
    e = ne['coordinates'][0]
    sw = geojson_utils.destination_point(start, 225, corner_dist)
    s = sw['coordinates'][1]
    w = sw['coordinates'][0]
    return [s,w,n,e]

  @staticmethod
  def distance_to_geometry(lat, lng, geometry):
    target = GeoUtil.make_point(lat, lng)
    t = geometry['type']
    if t == 'Point':
      point_coords = [geometry['coordinates']]
    elif t == 'LineString':
      point_coords = geometry['coordinates']
    elif t == 'Polygon':
      inside = geojson_utils.point_in_polygon(target, geometry)
      if inside: return 0
      point_coords = GeoUtil._points_for_polygon(geometry)
    elif t == 'MultiPolygon':
      inside = geojson_utils.point_in_multipolygon(target, geometry)
      if inside: return 0
      point_coords = []
      polygon = {}
      for coords in geometry['coordinates']:
        polygon['coordinates'] = coords
        point_coords += GeoUtil._points_for_polygon(polygon)
    else:
      print(f'Unsupported geometry type: {t}')
      point_coords = []

    point = {}
    min_dist = float('inf')
    for coordinates in point_coords:
      point['coordinates'] = coordinates
      dist = geojson_utils.point_distance(point, target)
      if dist < min_dist:
        min_dist = dist
    return min_dist / 1000

  @staticmethod
  def min_distance_osm_element(lat, lng, json_geometries):
    feature_collection = json2geojson(json_geometries)
    min_dist = float('inf')
    element = None
    for feature in feature_collection['features']:
      geometry = feature['geometry']
      dist = GeoUtil.distance_to_geometry(lat, lng, geometry)
      if dist < min_dist:
        min_dist = dist
        properties = feature['properties']
        element = OSMElement(properties['id'], properties['type'])
        if dist == 0:
          break
    return (min_dist, element)

  @staticmethod
  def _points_for_polygon(polygon):
    coords = polygon['coordinates']
    point_coords = []
    if len(coords) > 0:
      for coord_pair in coords[0]:
        point_coords.append(coord_pair)
    return point_coords
