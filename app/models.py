from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class GuestLog(Base):
    __tablename__ = "guest_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
