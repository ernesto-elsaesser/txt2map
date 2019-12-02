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
  def geometry_within_radius(lat, lng, geometry, radius):
    target = GeoUtil.make_point(lat, lng)
    t = geometry['type']
    if t in ['Point', 'LineString']:
      return geojson_utils.geometry_within_radius(geometry, target, radius * 1000)
    elif t == 'Polygon':
      return geojson_utils.point_in_polygon(target, geometry)
    elif t == 'MultiPolygon':
      return geojson_utils.point_in_multipolygon(target, geometry)
    else:
      print(f'Unsupported geometry type: {t}')
      return False


