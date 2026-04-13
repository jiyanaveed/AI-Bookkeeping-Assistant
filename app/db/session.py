from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings

_settings = get_settings()

# SQLite needs check_same_thread=False for FastAPI; Postgres ignores it.
_connect_args = {}
if _settings.sqlalchemy_database_url.lower().startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _settings.sqlalchemy_database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they do not exist (v1 — no Alembic)."""
    from app.db.base import Base
    from app.db.migrate_sqlite import apply_sqlite_migrations
    from app.models import db_models  # noqa: F401 — register ORM mappings

    Base.metadata.create_all(bind=engine)
    apply_sqlite_migrations(engine)
