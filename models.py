# http://flask.pocoo.org/docs/0.12/patterns/sqlalchemy/

from sqlalchemy import Column, Integer, String, ForeignKey
from flask_login import UserMixin
from database import Base

class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)

    def __init__(self, username=None, email=None, password=None):
        self.username = username
        self.email = email
        self.password = password

    def __repr__(self):
        return "<User %r>" % (self.username)

class Platform(Base):
	__tablename__ = "platforms"
	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)

	def __init__(self, name):
		self.name = name

class UserPlatform(Base):
	__tablename__ = "user_platforms"
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)

	def __init__(self, user_id, platform_id):
		self.user_id = user_id
		self.platform_id = platform_id

class Game(Base):
	__tablename__ = "games"
	id = Column(Integer, primary_key=True)
	igdb_id = Column(Integer, nullable=False)
	name = Column(String, nullable=False)
	image_url = Column(String, nullable=False)

	def __init__(self, igdb_id, name, image_url):
		self.igdb_id = igdb_id
		self.name = name
		self.image_url = image_url

class ListEntry(Base):
	__tablename__ = "list_entries"
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
	platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
	list_type = Column(String, nullable=False)

	def __init__(self, user_id, game_id, platform_id, list_type):
		self.user_id = user_id
		self.game_id = game_id
		self.platform_id = platform_id
		self.list_type = list_type
