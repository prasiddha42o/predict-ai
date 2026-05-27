"""SQLAlchemy engine, session factory and declarative base.

`DATABASE_URL` defaults to a local SQLite file so the app and the test suite
run with zero setup; docker-compose points it at the postgres service
instead. Nothing else in the app should construct an engine or a session --
route handlers depend on `get_db`, everything else imports `SessionLocal`.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
