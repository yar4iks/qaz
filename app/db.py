import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./app.db")


def create_db_engine():
    database_url = get_database_url()
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, connect_args=connect_args)


ENGINE = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)


def init_db() -> None:
    from app import models

    Base.metadata.create_all(bind=ENGINE)
