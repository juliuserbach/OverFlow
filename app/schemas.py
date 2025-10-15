from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class GuestLogSchema(BaseModel):
    recorded_at: dt.datetime
    count: int
    capacity: int | None

    class Config:
        from_attributes = True


class DailySummarySchema(BaseModel):
    date: dt.date
    average: float | None
    max: int | None
    min: int | None


class LogResponse(BaseModel):
    success: bool
    count: int
    capacity: int | None
    recorded_at: dt.datetime
