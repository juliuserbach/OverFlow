# OverFlow – Pool Guest Logger

This project provides a small service to fetch, store, and visualize the number of guests ("Anzahl Gäste") published for the Hallenbad City indoor pool in Zürich.

## Features

- Async scraper that retrieves the latest guest count from the official website.
- SQLite-backed database to keep a historical log of guest counts and capacity values.
- FastAPI web service exposing JSON endpoints and a simple frontend dashboard (Chart.js) for quick visualization.
- CLI helper (`scripts/log_guest_count.py`) that can be scheduled via cron or Home Assistant automations.

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```

2. **Initialize the database and log a value**

   ```bash
   python scripts/log_guest_count.py
   ```

   The database is stored by default at `data/guest_logs.db`. Override the location with the `POOL_LOGGER_DB` environment variable if desired.

## Debugging

- Increase verbosity by setting `POOL_LOGGER_LOG_LEVEL=DEBUG` when running the CLI. Example:
  `POOL_LOGGER_LOG_LEVEL=DEBUG python scripts/log_guest_count.py`
- On parse failures, the last fetched HTML is saved to `data/last_response.html` for inspection.
- The page uses a WebSocket to populate the live guest count. If the number is not present in the static HTML, the scraper falls back to the official WebSocket at `wss://badi-public.crowdmonitor.ch:9591/api` to retrieve `currentfill` and `maxspace`.

3. **Run the web server**

   ```bash
   uvicorn app.main:app --reload
   ```

   Visit [http://localhost:8000](http://localhost:8000) to see the dashboard. The following API endpoints are available:

   - `GET /api/latest` – Latest recorded data point.
   - `GET /api/history?limit=200` – Recent history for visualization or external use.
   - `GET /api/daily?days=14` – Daily aggregates (average/min/max).
   - `POST /api/log` – Fetch the current value from the website and store it.

## Home Assistant Integration

- Call the `POST /api/log` endpoint from an automation (e.g. via a `rest_command`) to schedule periodic updates.
- Use the `GET /api/history` endpoint with a [RESTful sensor](https://www.home-assistant.io/integrations/rest/) to surface the data inside Home Assistant.
- Embed the dashboard into a panel using the [Webpage card](https://www.home-assistant.io/lovelace/iframe/) pointing to the running FastAPI service.

## Testing

Run unit tests with:

```bash
pytest
```

## Configuration

Environment variables:

- `POOL_LOGGER_TARGET_URL` – Override the scraping URL if it ever changes.
- `POOL_LOGGER_USER_AGENT` – Customize the HTTP User-Agent header.
- `POOL_LOGGER_DB` – Path to the SQLite database file.
