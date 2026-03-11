from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import GuestLog, Pool


def upsert_pool(session: Session, *, uid: str, name: str, category: str | None = None) -> Pool:
    pool = session.get(Pool, uid)
    if pool is None:
        pool = Pool(uid=uid, name=name, category=category)
        session.add(pool)
    else:
        pool.name = name
        pool.category = category
    return pool


def log_guest_count(
    session: Session, *, pool_uid: str | None, timestamp: dt.datetime, count: int, capacity: int | None
) -> GuestLog:
    entry = GuestLog(recorded_at=timestamp, count=count, capacity=capacity, pool_uid=pool_uid)
    session.add(entry)
    return entry


def get_latest(session: Session) -> GuestLog | None:
    return session.scalar(select(GuestLog).order_by(GuestLog.recorded_at.desc()).limit(1))


def get_latest_for_pool(session: Session, *, pool_uid: str) -> GuestLog | None:
    stmt = select(GuestLog).where(GuestLog.pool_uid == pool_uid).order_by(GuestLog.recorded_at.desc()).limit(1)
    return session.scalar(stmt)


def list_entries(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    before: dt.datetime | None = None,
    pool_uid: str | None = None,
) -> list[GuestLog]:
    """Return log entries ordered newest-first.

    Args:
        limit: Maximum number of rows to return.
        offset: Number of rows to skip (simple offset-based pagination).
            When combined with ``before``, the offset is applied after the
            cursor filter — use one strategy at a time for predictable results.
        before: Datetime cursor — only entries recorded strictly before this
            timestamp are returned (cursor-based pagination).
        pool_uid: Filter to a specific pool when provided.
    """
    stmt = select(GuestLog)
    if pool_uid is not None:
        stmt = stmt.where(GuestLog.pool_uid == pool_uid)
    if before is not None:
        stmt = stmt.where(GuestLog.recorded_at < before)
    stmt = stmt.order_by(GuestLog.recorded_at.desc()).offset(offset).limit(limit)
    return list(session.scalars(stmt))


def daily_summary(session: Session, *, days: int = 7, pool_uid: str | None = None) -> list[dict[str, int | float | None]]:
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    stmt = (
        select(
            func.date(GuestLog.recorded_at).label("date"),
            func.avg(GuestLog.count).label("avg"),
            func.max(GuestLog.count).label("max"),
            func.min(GuestLog.count).label("min"),
        )
        .where(GuestLog.recorded_at >= cutoff)
    )
    if pool_uid is not None:
        stmt = stmt.where(GuestLog.pool_uid == pool_uid)
    stmt = stmt.group_by(func.date(GuestLog.recorded_at)).order_by(func.date(GuestLog.recorded_at))
    results = session.execute(stmt)
    return [
        {
            "date": row.date,
            "average": float(row.avg) if row.avg is not None else None,
            "max": row.max,
            "min": row.min,
        }
        for row in results
    ]


def list_pools(session: Session) -> list[Pool]:
    return list(session.scalars(select(Pool).order_by(Pool.name)))
