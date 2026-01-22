import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SessionLocal = None
ENGINE = None


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./app.db")


def init_engine(database_url: str | None = None) -> None:
    global ENGINE, SessionLocal
    database_url = database_url or get_database_url()
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    ENGINE = create_engine(database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
