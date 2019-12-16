import geojson_utils
from .model import OSMElement

class GeoUtil:

  @staticmethod
  def geojson_point(lat, lng):
      return {'type': 'Point', 'coordinates': [lng, lat]}

  @staticmethod
  def geojson_polygon(lat_lngs):
      coords = [[lng, lat] for lat, lng in lat_lngs]
      return {'type': 'Polygon', 'coordinates': [coords]}

  @staticmethod
  def bounding_box(lat, lng, corner_dist):
    start = GeoUtil.geojson_point(lat, lng)
    ne = geojson_utils.destination_point(start, 45, corner_dist)
    n = ne['coordinates'][1]
    e = ne['coordinates'][0]
    sw = geojson_utils.destination_point(start, 225, corner_dist)
    s = sw['coordinates'][1]
    w = sw['coordinates'][0]
    return [s,w,n,e]

  @staticmethod
  def distance(lat1, lng1, lat2, lng2):
    p1 = GeoUtil.geojson_point(lat1, lng1)
    p2 = GeoUtil.geojson_point(lat2, lng2)
    dist = geojson_utils.point_distance(p1, p2)
    return dist / 1000

  @staticmethod
  def minimum_distance(lat, lng, lat_lngs):

    if len(lat_lngs) > 2 and lat_lngs[0] == lat_lngs[-1]:
      point = GeoUtil.geojson_point(lat, lng)
      polygon = GeoUtil.geojson_polygon(lat_lngs)
      is_inside = geojson_utils.point_in_polygon(point, polygon)
      if is_inside:
        return 0

    min_dist = float('inf')
    for lat2, lng2 in lat_lngs:
      dist = GeoUtil.distance(lat, lng, lat2, lng2)
      if dist == 0:
        return 0
      if dist < min_dist:
        min_dist = dist

    return min_dist

  @staticmethod
  def osm_element_distance(lat, lng, el):
    t = el['type']
    if t == 'node':
      return GeoUtil.distance(lat, lng, el['lat'], el['lon'])
    elif t == 'way':
      lat_lngs = [(p['lat'], p['lon']) for p in el['geometry']]
      return GeoUtil.minimum_distance(lat, lng, lat_lngs)
    elif t == 'relation':
      distances = []
      for m in el['members']:
        if m['role'] in ['label', 'admin_centre', 'subarea', 'inner']:
          continue
        if m['type'] == 'relation':
          print('Super-relations not supported!')
          continue
        dist = GeoUtil.osm_element_distance(lat, lng, m)
        distances.append(dist)
        if dist == 0:
          break
      if len(distances) == 0:
        return float('inf')
      return min(distances)
