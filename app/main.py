from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import crud
from .database import SessionLocal, Base, ENGINE
from .schemas import DailySummarySchema, GuestLogSchema, LogResponse
from .scraper import GuestCountError, fetch_guest_count_async

Base.metadata.create_all(bind=ENGINE)

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


@app.get("/api/latest", response_model=GuestLogSchema | None)
async def api_latest(session=Depends(get_session)):
    return crud.get_latest(session)


@app.get("/api/history", response_model=list[GuestLogSchema])
async def api_history(limit: int = 100, session=Depends(get_session)):
    limit = max(1, min(limit, 1000))
    return crud.list_entries(session, limit=limit)


@app.get("/api/daily", response_model=list[DailySummarySchema])
async def api_daily(days: int = 7, session=Depends(get_session)):
    days = max(1, min(days, 90))
    return crud.daily_summary(session, days=days)


@app.post("/api/log", response_model=LogResponse)
async def api_log(session=Depends(get_session)):
    try:
        guest_count = await fetch_guest_count_async()
    except GuestCountError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    entry = crud.log_guest_count(
        session,
        timestamp=guest_count.timestamp,
        count=guest_count.count,
        capacity=guest_count.capacity,
    )
    session.commit()
    session.refresh(entry)

    return LogResponse(
        success=True,
        count=entry.count,
        capacity=entry.capacity,
        recorded_at=entry.recorded_at,
    )


@app.on_event("startup")
async def warmup_cache():
    # Fetch latest entry if DB empty to provide quick data on startup (non-blocking)
    async def _ensure_latest():
        with SessionLocal() as session:
            if crud.get_latest(session) is None:
                try:
                    guest_count = await fetch_guest_count_async()
                except GuestCountError:
                    return
                crud.log_guest_count(
                    session,
                    timestamp=guest_count.timestamp,
                    count=guest_count.count,
                    capacity=guest_count.capacity,
                )
                session.commit()

    asyncio.create_task(_ensure_latest())
