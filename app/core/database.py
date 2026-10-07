from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def _build_engine():
    engine_kwargs = {"echo": settings.DB_ECHO, "pool_pre_ping": True}
    if settings.DATABASE_URL.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.DATABASE_URL, **engine_kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_database_ready() -> None:
    """Rebuild the local SQLite schema so stale database files do not leave mismatched columns behind."""
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
