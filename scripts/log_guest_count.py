from __future__ import annotations

import asyncio
import logging

import os

from app import crud
from app.database import SessionLocal, Base, ENGINE
from app.scraper import GuestCountError, fetch_guest_count_async

log_level_name = os.getenv("POOL_LOGGER_LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")

Base.metadata.create_all(bind=ENGINE)


async def main() -> None:
    try:
        guest_count = await fetch_guest_count_async()
    except GuestCountError as exc:
        logging.error("Failed to fetch guest count: %s", exc)
        raise SystemExit(1) from exc

    with SessionLocal() as session:
        entry = crud.log_guest_count(
            session,
            timestamp=guest_count.timestamp,
            count=guest_count.count,
            capacity=guest_count.capacity,
        )
        session.commit()
        logging.info("Logged %s guests at %s", entry.count, entry.recorded_at.isoformat())


if __name__ == "__main__":
    asyncio.run(main())
