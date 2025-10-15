from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import GuestLog


def log_guest_count(session: Session, *, timestamp: dt.datetime, count: int, capacity: int | None) -> GuestLog:
    entry = GuestLog(recorded_at=timestamp, count=count, capacity=capacity)
    session.add(entry)
    return entry


def get_latest(session: Session) -> GuestLog | None:
    return session.scalar(select(GuestLog).order_by(GuestLog.recorded_at.desc()).limit(1))


def list_entries(session: Session, *, limit: int = 100) -> list[GuestLog]:
    stmt = select(GuestLog).order_by(GuestLog.recorded_at.desc()).limit(limit)
    return list(session.scalars(stmt))


def daily_summary(session: Session, *, days: int = 7) -> list[dict[str, int | float | None]]:
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    stmt = (
        select(
            func.date(GuestLog.recorded_at).label("date"),
            func.avg(GuestLog.count).label("avg"),
            func.max(GuestLog.count).label("max"),
            func.min(GuestLog.count).label("min"),
        )
        .where(GuestLog.recorded_at >= cutoff)
        .group_by(func.date(GuestLog.recorded_at))
        .order_by(func.date(GuestLog.recorded_at))
    )
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
