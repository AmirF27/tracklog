# http://flask.pocoo.org/docs/0.12/patterns/sqlalchemy/

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# http://docs.sqlalchemy.org/en/latest/core/engines.html
engine = create_engine('postgresql://ameer:27121991@localhost/tracklog')

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()
