import geojson_utils
import math
import re
import requests

class BoundingBox:

  def __init__(self, s, w, n, e):
    self.s = s
    self.w = w
    self.n = n
    self.e = e
    self.center_lat = (s + n) / 2
    self.center_lon = (w + e) / 2

  def __str__(self):
    return f'{self.s},{self.w},{self.n},{self.e}'

class GeoUtil:

  dbpedia_patterns = [
      ('<span property="geo:lat" xmlns:geo="http:\/\/www\.w3\.org\/2003\/01\/geo\/wgs84_pos#">([0-9\.\-]+)</span>',
       '<span property="geo:long" xmlns:geo="http:\/\/www\.w3\.org\/2003\/01\/geo\/wgs84_pos#">([0-9\.\-]+)</span>'),
      ('<span property="dbp:latitude">([0-9\.\-]+)<\/span>',
       '<span property="dbp:longitude">([0-9\.\-]+)<\/span>')
  ]

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
    return BoundingBox(s, w, n, e)

  @staticmethod
  def average_coord(coords):
    lat_sum = 0
    lon_sum = 0
    count = 0
    for lat, lon in coords:
      lat_sum += lat
      lon_sum += lon
      count += 1
    return (lat_sum/count, lon_sum/count)

  @staticmethod
  def point_in_bounding_box(lat, lon, bbox):
    return bbox.s < lat < bbox.n and bbox.w < lon < bbox.e

  @staticmethod
  def distance(lat1, lon1, lat2, lon2):
    p1 = GeoUtil.geojson_point(lat1, lon1)
    p2 = GeoUtil.geojson_point(lat2, lon2)
    dist = geojson_utils.point_distance(p1, p2)
    return dist / 1000

  @staticmethod
  def osm_minimum_distance(lat, lon, bb_data):
    min_dist = float('inf')
    for el in bb_data['elements']:
      t = el['type']
      if t == 'node':
        dist = GeoUtil.distance(lat, lon, el['lat'], el['lon'])
      else:
        b = el['bounds']
        if b['minlat'] < lat < b['maxlat'] and b['minlon'] < lon < b['maxlon']:
          return 0
        center_lat = (b['minlat'] + b['maxlat']) / 2
        center_lon = (b['minlon'] + b['maxlon']) / 2
        dist = GeoUtil.distance(lat, lon, center_lat, center_lon)
      if dist < min_dist:
        min_dist = dist
    return min_dist

  @staticmethod
  def coordinate_for_wiki_url(url):
    title = url.replace('https://en.wikipedia.org/wiki/', '')
    title = title.replace('_', ' ')
    req_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "coordinates"
    }
    resp = requests.get(url=req_url, params=params)
    data = resp.json()
    pages = data['query']['pages']

    for p in pages.values():
      if p['title'] != title:
        continue
      if 'coordinates' not in p:
        continue
      lat = p['coordinates'][0]['lat']
      lon = p['coordinates'][0]['lon']
      return (lat, lon)

    return None
      
