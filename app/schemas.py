from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class GuestLogSchema(BaseModel):
    recorded_at: dt.datetime
    count: int
    capacity: int | None
    pool_uid: str | None

    class Config:
        from_attributes = True


class DailySummarySchema(BaseModel):
    date: dt.date
    average: float | None
    max: int | None
    min: int | None


class LogResponse(BaseModel):
    success: bool
    entries: list[GuestLogSchema]


class PoolSchema(BaseModel):
    uid: str
    name: str
    category: str | None = None

    class Config:
        from_attributes = True
