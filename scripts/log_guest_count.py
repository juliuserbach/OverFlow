from __future__ import annotations

import asyncio
import logging

import os

from app import crud
from app.database import SessionLocal, ensure_schema
from app.scraper import GuestCountError, fetch_all_guest_counts_async

log_level_name = os.getenv("POOL_LOGGER_LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")

ensure_schema()


async def main() -> None:
    try:
        guest_counts = await fetch_all_guest_counts_async()
    except GuestCountError as exc:
        logging.error("Failed to fetch guest count: %s", exc)
        raise SystemExit(1) from exc

    with SessionLocal() as session:
        entries = []
        for item in guest_counts:
            if item.pool_uid and item.pool_name:
                crud.upsert_pool(session, uid=item.pool_uid, name=item.pool_name)
            entry = crud.log_guest_count(
                session,
                pool_uid=item.pool_uid,
                timestamp=item.timestamp,
                count=item.count,
                capacity=item.capacity,
            )
            entries.append(entry)
        session.commit()
        for entry in entries:
            logging.info(
                "Logged %s guests at %s for %s",
                entry.count,
                entry.recorded_at.isoformat(),
                entry.pool_uid or "unknown",
            )


if __name__ == "__main__":
    asyncio.run(main())
