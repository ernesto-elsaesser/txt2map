from database import NameDatabase
import requests

class GeoName:

  def __init__(self, json):
    self.id = json['geonameId']
    self.name = json['name']
    self.feature_class = json['fcl']
    self.feature_code = json['fcode']
    self.lat = float(json['lat'])
    self.lng = float(json['lng'])


class GeoNamesDatabase(NameDatabase):

  def __init__(self):
    super().__init__('data/geonames.db')

  def create_tables(self):
    self.cursor.execute(
        '''CREATE TABLE geonames (geoname_id BIGINT NOT NULL,
          names_rowid INTEGER NOT NULL)''')
    self.cursor.execute('CREATE INDEX geonames_index ON geonames(names_rowid)')
    super().create_tables()

  def insert_geoname(self, name, id):
      (rowid, _) = self.insert_name(name)
      if rowid != None:
        self.cursor.execute('INSERT INTO geonames VALUES(?, ?)', (id, rowid))

  def get_geoname_ids(self, name):
    rowid = self.get_rowid(name)
    self.cursor.execute(
        'SELECT geoname_id FROM geonames WHERE names_rowid = ?', (rowid, ))
    geoname_ids = []
    for row in self.cursor.fetchall():
      geoname_ids.append(row[0])
    return geoname_ids


class GeoNamesClient:

  api_url = 'http://api.geonames.org'

  def get_geoname(self, id):
    url = f'{self.api_url}/getJSON?geonameId={id}&username=map2txt'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    return GeoName(res.json())

  def get_hierarchy(self, id):
    url = f'{self.api_url}/hierarchyJSON?geonameId={id}&username=map2txt'
    res = requests.get(url=url)
    res.encoding = 'utf-8'
    json_dict = res.json()
    geonames_array = json_dict['geonames']
    return list(map(lambda d: GeoName(d), geonames_array))
