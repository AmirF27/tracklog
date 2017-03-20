from models import *
from database import Base, engine

# create database
Base.metadata.create_all(bind=engine)
