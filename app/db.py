import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


DATABASE_URL = os.environ["DATABASE_URL"]

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)