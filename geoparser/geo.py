import geojson_utils

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
  def min_distance_beyond_tolerance(lat, lng, feature_collection, tolerance_km):
    min_dist = float('inf')
    for feature in feature_collection['features']:
      geometry = feature['geometry']
      dist = GeoUtil.distance_beyond_tolerance(lat, lng, geometry, tolerance_km)
      if dist == 0:
        return 0
      elif dist < min_dist:
        min_dist = dist
    return min_dist

  @staticmethod
  def distance_beyond_tolerance(lat, lng, geometry, tolerance_km):
    target = GeoUtil.make_point(lat, lng)
    t = geometry['type']
    if t == 'Point':
      point_coords = [geometry['coordinates']]
    elif t == 'LineString':
      point_coords = geometry['coordinates']
    elif t == 'Polygon':
      inside = geojson_utils.point_in_polygon(target, geometry)
      if inside: return 0
      centroid = geojson_utils.centroid(geometry)
      point_coords = [centroid['coordinates']]
    elif t == 'MultiPolygon':
      inside = geojson_utils.point_in_multipolygon(target, geometry)
      if inside: return 0
      point_coords = []
      polygon = {}
      for coords in geometry['coordinates']:
        polygon['coordinates'] = coords
        centroid = geojson_utils.centroid(polygon)
        point_coords.append(centroid['coordinates'])
    else:
      print(f'Unsupported geometry type: {t}')
      point_coords = []

    point = {}
    min_dist = float('inf')
    limit = tolerance_km * 1000 
    for coordinates in point_coords:
      point['coordinates'] = coordinates
      dist = geojson_utils.point_distance(point, target)
      if dist < limit:
        return 0
      elif dist < min_dist:
        min_dist = dist
    return (min_dist / 1000) - tolerance_km
