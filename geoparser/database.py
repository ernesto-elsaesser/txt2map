import sqlite3

class Database:

  def __init__(self, sqlite_db):
    self.db = sqlite_db
    self.cursor = sqlite_db.cursor()

  def __del__(self):
    self.db.close()

  def commit_changes(self):
    self.db.commit()
