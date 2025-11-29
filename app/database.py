from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_database_url


class Base(DeclarativeBase):
    pass


def _create_engine():
    return create_engine(get_database_url(), future=True, echo=False)


ENGINE = _create_engine()
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


def ensure_schema() -> None:
    """Ensure required tables/columns exist (lightweight, SQLite-friendly)."""

    with ENGINE.begin() as conn:
        # Create missing tables
        Base.metadata.create_all(bind=conn)

        # Add pool_uid column to guest_logs if absent
        result = conn.execute(text("PRAGMA table_info(guest_logs)"))
        cols = [row[1] for row in result]  # type: ignore[index]
        if "pool_uid" not in cols:
            conn.execute(text("ALTER TABLE guest_logs ADD COLUMN pool_uid TEXT"))


@contextmanager
def session_scope() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - passthrough to raise after rollback
        session.rollback()
        raise
    finally:
        session.close()
