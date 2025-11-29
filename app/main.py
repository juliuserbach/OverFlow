from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import crud
from .database import SessionLocal, ensure_schema
from .schemas import DailySummarySchema, GuestLogSchema, LogResponse, PoolSchema
from .scraper import GuestCountError, fetch_all_guest_counts_async

ensure_schema()

app = FastAPI(title="City Indoor Pool Guest Logger")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/pools", response_model=list[PoolSchema])
async def api_pools(session=Depends(get_session)):
    return crud.list_pools(session)


@app.get("/api/latest", response_model=GuestLogSchema | None)
async def api_latest(pool: str | None = None, session=Depends(get_session)):
    if pool:
        return crud.get_latest_for_pool(session, pool_uid=pool)
    return crud.get_latest(session)


@app.get("/api/history", response_model=list[GuestLogSchema])
async def api_history(limit: int = 100, pool: str | None = None, session=Depends(get_session)):
    limit = max(1, min(limit, 1000))
    return crud.list_entries(session, limit=limit, pool_uid=pool)


@app.get("/api/daily", response_model=list[DailySummarySchema])
async def api_daily(days: int = 7, pool: str | None = None, session=Depends(get_session)):
    days = max(1, min(days, 90))
    return crud.daily_summary(session, days=days, pool_uid=pool)


@app.post("/api/log", response_model=LogResponse)
async def api_log(session=Depends(get_session)):
    try:
        guest_counts = await fetch_all_guest_counts_async()
    except GuestCountError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    entries: list = []
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
        session.refresh(entry)

    return LogResponse(success=True, entries=entries)


@app.on_event("startup")
async def warmup_cache():
    # Fetch latest entry if DB empty to provide quick data on startup (non-blocking)
    async def _ensure_latest():
        with SessionLocal() as session:
            if crud.get_latest(session) is None:
                try:
                    guest_counts = await fetch_all_guest_counts_async()
                except GuestCountError:
                    return
                for item in guest_counts:
                    if item.pool_uid and item.pool_name:
                        crud.upsert_pool(session, uid=item.pool_uid, name=item.pool_name)
                    crud.log_guest_count(
                        session,
                        pool_uid=item.pool_uid,
                        timestamp=item.timestamp,
                        count=item.count,
                        capacity=item.capacity,
                    )
                session.commit()

    asyncio.create_task(_ensure_latest())
