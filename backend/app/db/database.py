"""
Database engine & session setup (SQLAlchemy 2.0).

Uses the DATABASE_URL environment variable when set, e.g.
    postgresql+psycopg2://user:pass@localhost:5432/worldcup
Falls back to a local SQLite file so the project runs with zero setup.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DEFAULT_SQLITE = "sqlite:///" + os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "worldcup.db",
)
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE)

# check_same_thread is a SQLite-only flag; harmless to omit for Postgres
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
