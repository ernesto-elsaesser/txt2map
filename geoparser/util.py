import geojson_utils
import math
import re
import requests

class GeoUtil:

  @staticmethod
  def geojson_point(lat, lon):
      return {'type': 'Point', 'coordinates': [lon, lat]}

  @staticmethod
  def geojson_polygon(lat_lons):
      coords = [[lon, lat] for lat, lon in lat_lons]
      return {'type': 'Polygon', 'coordinates': [coords]}

  @staticmethod
  def bounding_box(lat, lon, corner_dist):
    start = GeoUtil.geojson_point(lat, lon)
    ne = geojson_utils.destination_point(start, 45, corner_dist)
    n = ne['coordinates'][1]
    e = ne['coordinates'][0]
    sw = geojson_utils.destination_point(start, 225, corner_dist)
    s = sw['coordinates'][1]
    w = sw['coordinates'][0]
    return [s,w,n,e]

  @staticmethod
  def distance(lat1, lon1, lat2, lon2):
    p1 = GeoUtil.geojson_point(lat1, lon1)
    p2 = GeoUtil.geojson_point(lat2, lon2)
    dist = geojson_utils.point_distance(p1, p2)
    return dist / 1000

  @staticmethod
  def minimum_distance(lat, lon, lat_lons):
    l = len(lat_lons)

    if l > 2 and lat_lons[0] == lat_lons[-1]:
      point = GeoUtil.geojson_point(lat, lon)
      polygon = GeoUtil.geojson_polygon(lat_lons)
      is_inside = geojson_utils.point_in_polygon(point, polygon)
      if is_inside:
        return 0

    min_dist = float('inf')
    step = int(math.ceil(l / 10))
    for idx in range(0, l, step):
      (lat2, lon2) = lat_lons[idx]
      dist = GeoUtil.distance(lat, lon, lat2, lon2)
      if dist == 0:
        return 0
      if dist < min_dist:
        min_dist = dist

    return min_dist

  @staticmethod
  def osm_element_distance(lat, lon, el):
    t = el['type']
    if t == 'node':
      return GeoUtil.distance(lat, lon, el['lat'], el['lon'])
    elif t == 'way':
      lat_lons = [(p['lat'], p['lon']) for p in el['geometry']]
      return GeoUtil.minimum_distance(lat, lon, lat_lons)
    elif t == 'relation':
      distances = []
      for m in el['members']:
        if m['role'] in ['label', 'admin_centre', 'subarea', 'inner']:
          continue
        if m['type'] == 'relation':
          print('Super-relations not supported!')
          continue
        dist = GeoUtil.osm_element_distance(lat, lon, m)
        distances.append(dist)
        if dist == 0:
          break
      if len(distances) == 0:
        return float('inf')
      return min(distances)


class WikiUtil:

  patterns = [
      ('<span property="geo:lat" xmlns:geo="http:\/\/www\.w3\.org\/2003\/01\/geo\/wgs84_pos#">([0-9\.\-]+)</span>',
       '<span property="geo:long" xmlns:geo="http:\/\/www\.w3\.org\/2003\/01\/geo\/wgs84_pos#">([0-9\.\-]+)</span>'),
      ('<span property="dbp:latitude">([0-9\.\-]+)<\/span>',
       '<span property="dbp:longitude">([0-9\.\-]+)<\/span>')
  ]

  @staticmethod
  def coordinates_for_url(url):
    dbpedia_url = url.replace('https://en.wikipedia.org/wiki',
                         'http://dbpedia.org/page')
    resp = requests.get(url=dbpedia_url)
    html = resp.text
    coords = []

    for lat_pat, lon_pat in WikiUtil.patterns:
      lat_matches = list(re.findall(lat_pat, html))
      lon_matches = list(re.findall(lon_pat, html))
      num = len(lat_matches)
      assert num == len(lon_matches)
      if num == 1:
        lat = float(lat_matches[0])
        lon = float(lon_matches[0])
        coords.append((lat, lon))
      elif num == 2:
        min_lat = float(lat_matches[0])
        min_lon = float(lon_matches[0])
        max_lat = float(lat_matches[1])
        max_lon = float(lon_matches[1])
        lat = (min_lat + max_lat) / 2
        lon = (min_lon + max_lon) / 2
        coords.append((lat, lon))

    return coords