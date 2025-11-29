from __future__ import annotations

import asyncio
import datetime as dt
import logging
import re
from dataclasses import dataclass

import importlib
from html import unescape
from typing import TYPE_CHECKING

from .config import get_target_url, get_user_agent, get_ws_url

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    import httpx


@dataclass(slots=True)
class GuestCount:
    timestamp: dt.datetime
    count: int
    capacity: int | None = None
    pool_uid: str | None = None
    pool_name: str | None = None


class GuestCountError(RuntimeError):
    """Raised when the guest count cannot be retrieved."""


COUNT_PATTERN = re.compile(r"Anzahl\s+G[äa]ste[^0-9]*(\d+)", re.IGNORECASE)
# Match the dynamic visitor number cell rendered by the component when present.
# Be tolerant to whitespace and to the numeric UID segment (e.g. SSD-4, SSD-12, ...).
COUNT_ID_PATTERN = re.compile(
    r"<td[^>]*id=[\"']SSD-(?:\d+)_visitornumber[\"'][^>]*>\s*(\d+)\s*<",
    re.IGNORECASE,
)
UID_IN_MARKUP_PATTERN = re.compile(r"(SSD-\d+)_visitornumber")
CAPACITY_PATTERN = re.compile(r"(?:max\.?\s*)?(?:Kapazit[aä]t|von)\s*(\d+)", re.IGNORECASE)
POOLS_TABLE_PATTERN = re.compile(
    r'id="baederinfossummary"[^>]*rows="(?P<rows>\[\[.*?\])"', re.IGNORECASE | re.DOTALL
)


async def fetch_guest_count_async(client: "httpx.AsyncClient | None" = None) -> GuestCount:
    """Fetch a single guest count (first available pool)."""

    results = await fetch_all_guest_counts_async(client=client)
    if not results:
        raise GuestCountError("No guest counts available")
    return results[0]


async def fetch_all_guest_counts_async(client: "httpx.AsyncClient | None" = None) -> list[GuestCount]:
    """Fetch guest counts for all pools."""

    try:
        httpx = importlib.import_module("httpx")
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency missing
        raise GuestCountError(
            "The 'httpx' package is required to fetch guest counts. Install the project "
            "dependencies to enable network scraping."
        ) from exc

    close_client = False
    async_client: "httpx.AsyncClient"
    if client is None:
        headers = {"User-Agent": get_user_agent(), "Accept-Language": "de"}
        async_client = httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True)
        close_client = True
    else:
        async_client = client

    try:
        url = get_target_url()
        logger.debug("Fetching guest count from %s", url)
        response = await async_client.get(url)
        response.raise_for_status()
        html = response.text

        pools = _extract_pools_from_html(html)
        if not pools:
            _maybe_dump_html_for_debug(html)
            raise GuestCountError("Could not find pools in page")

        counts = await _fetch_counts_via_websocket(pools)
        if not counts:
            raise GuestCountError("Could not find guest counts in WebSocket stream")

        logger.info("Fetched guest counts for %s pools", len(counts))
        return counts
    except httpx.HTTPError as exc:  # pragma: no cover - network errors
        logger.exception("HTTP error while fetching guest count")
        raise GuestCountError("Failed to fetch guest count") from exc
    finally:
        if close_client:
            await async_client.aclose()


def fetch_guest_count() -> GuestCount:
    """Synchronous helper for fetching guest counts."""

    return asyncio.run(fetch_guest_count_async())


__all__ = [
    "GuestCount",
    "GuestCountError",
    "fetch_guest_count",
    "fetch_guest_count_async",
    "fetch_all_guest_counts_async",
]


def _extract_visible_text(html: str) -> str:
    """Return a normalized, tag-free representation of the HTML content."""

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return unescape(text).strip()


def _extract_uid_from_html(html: str) -> str | None:
    """Extract the pool UID (e.g., 'SSD-4') from static markup.

    The page embeds a <stzh-datatable> with JSON-encoded rows that include
    ids like "SSD-4_visitornumber". We use this to determine the UID and
    then fetch live data via the WebSocket endpoint.
    """
    m = UID_IN_MARKUP_PATTERN.search(html)
    return m.group(1) if m else None


def _maybe_dump_html_for_debug(html: str) -> None:
    """Write the last fetched HTML to disk to aid debugging."""
    try:
        from pathlib import Path

        out_dir = Path("data")
        out_dir.mkdir(parents=True, exist_ok=True)
        dump_path = out_dir / "last_response.html"
        dump_path.write_text(html, encoding="utf-8")
        logger.debug("Wrote HTML response to %s for debugging", dump_path)
    except Exception:  # pragma: no cover - best-effort debug aid
        logger.debug("Failed to write HTML debug dump", exc_info=True)


async def _fetch_count_via_websocket(uid: str) -> tuple[int, int | None]:
    """Connect to the CrowdMonitor WebSocket and read current count and capacity.

    Returns
    -------
    (count, capacity)
        The current fill (guest count) and the maximum capacity if available.
    """
    try:
        websockets = importlib.import_module("websockets")
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise GuestCountError(
            "WebSocket fallback requires the 'websockets' package. Install project dependencies."
        ) from exc

    ws_url = get_ws_url()
    headers = [("User-Agent", get_user_agent())]

    async def _recv_once(ws) -> tuple[int, int | None] | None:
        import json

        raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
        payload = json.loads(raw)
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("uid") == uid:
                    # Values are strings; be tolerant when casting
                    current = item.get("currentfill")
                    maxspace = item.get("maxspace")
                    try:
                        count_val = int(float(current))
                    except Exception:
                        return None
                    capacity_val = None
                    try:
                        capacity_val = int(float(maxspace)) if maxspace is not None else None
                    except Exception:
                        capacity_val = None
                    return (count_val, capacity_val)
        return None

    try:
        # Support different websockets versions: some expect 'additional_headers', older
        # versions expect 'extra_headers'. Detect via signature to avoid TypeError.
        import inspect

        connect_sig = inspect.signature(websockets.connect)
        connect_kwargs: dict[str, object] = {}
        if "additional_headers" in connect_sig.parameters:
            connect_kwargs["additional_headers"] = headers
        elif "extra_headers" in connect_sig.parameters:
            connect_kwargs["extra_headers"] = headers

        async with websockets.connect(ws_url, **connect_kwargs) as ws:
            await ws.send("all")
            # First response usually contains the full snapshot
            result = await _recv_once(ws)
            if result is not None:
                return result
            # If not found, try a couple more messages briefly
            for _ in range(2):
                result = await _recv_once(ws)
                if result is not None:
                    return result
    except Exception as exc:  # pragma: no cover - network runtime
        logger.exception("WebSocket error while fetching guest count")
        raise GuestCountError("Failed to fetch guest count via WebSocket") from exc

    raise GuestCountError("Could not find guest count in WebSocket stream")


def _extract_pools_from_html(html: str) -> dict[str, str]:
    """Return mapping of pool uid -> pool name from the summary table markup."""

    m = POOLS_TABLE_PATTERN.search(html)
    if not m:
        return {}

    import json

    raw = m.group("rows").replace("&#34;", '"')
    try:
        rows = json.loads(raw)
    except Exception:
        return {}

    pools: dict[str, str] = {}
    for row in rows:
        try:
            name_html = row[0]["value"]
            uid = row[1]["id"]
        except Exception:
            continue
        name = _strip_tags(unescape(name_html))
        pools[uid] = name
    return pools


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def _fetch_counts_via_websocket(pools: dict[str, str]) -> list[GuestCount]:
    """Fetch counts for all pools via one WebSocket call."""

    results: list[GuestCount] = []
    for uid, name in pools.items():
        try:
            count, capacity = await _fetch_count_via_websocket(uid)
        except GuestCountError:
            continue
        results.append(
            GuestCount(
                timestamp=dt.datetime.now(dt.timezone.utc),
                count=count,
                capacity=capacity,
                pool_uid=uid,
                pool_name=name,
            )
        )
    return results
