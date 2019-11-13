import sqlite3
from model import Document

class NameDatabase:

  def __init__(self, path):
    self.db = sqlite3.connect(path)
    self.cursor = self.db.cursor()
    self.cursor.execute('PRAGMA case_sensitive_like = true')

  def __del__(self):
    self.db.close()

  def create_tables(self):
    self.cursor.execute(
        'CREATE TABLE names (name VARCHAR(100) NOT NULL UNIQUE)')
    self.cursor.execute('CREATE INDEX names_index ON names(name)')
    self.commit_changes()

  def insert_name(self, name):
    if name == '' or not Document.is_anchor(name, 0):
      return (None, False)
    try:
      self.cursor.execute('INSERT INTO names VALUES (?)', (name, ))
      return (self.cursor.lastrowid, True)
    except sqlite3.Error:
      rowid = self.get_rowid(name)
      return (rowid, False)

  def commit_changes(self):
    self.db.commit()

  def find_names(self, prefix):
    self.cursor.execute(
        'SELECT * FROM names WHERE name LIKE ?', (prefix + '%', ))
    return list(map(lambda r: r[0], self.cursor.fetchall()))

  def get_rowid(self, name):
    self.cursor.execute('SELECT rowid FROM names WHERE name = ?', (name, ))
    return self.cursor.fetchone()[0]
