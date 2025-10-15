from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_database_url


class Base(DeclarativeBase):
    pass


def _create_engine():
    return create_engine(get_database_url(), future=True, echo=False)


ENGINE = _create_engine()
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


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
