from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Pool(Base):
    __tablename__ = "pools"

    uid: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)

    logs: Mapped[list["GuestLog"]] = relationship(back_populates="pool")


class GuestLog(Base):
    __tablename__ = "guest_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pool_uid: Mapped[str | None] = mapped_column(String, ForeignKey("pools.uid"), nullable=True, index=True)

    pool: Mapped[Pool | None] = relationship(back_populates="logs")
