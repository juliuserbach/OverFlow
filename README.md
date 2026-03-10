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

## Docker

- **Build the image**

  ```bash
  docker build -t pool-guest-logger .
  ```

- **Run the API server** (persists the SQLite DB under `./data`):

  ```bash
  docker run -d \
    -p 8000:8000 \
    -v "$(pwd)/data:/data" \
    --restart unless-stopped \
    --name pool-guest-logger \
    pool-guest-logger
  ```

- **Using Docker Compose**

  ```bash
  docker compose up --build -d
  ```

  The compose file maps the database volume, exposes port `8000`, enables automatic restarts (`unless-stopped`), and sets a default log level. Tweak environment variables in `docker-compose.yml` as needed (e.g., target URL, API key headers).

- **Trigger a manual scrape inside the container**

  ```bash
  docker compose run --rm pool-guest-logger python scripts/log_guest_count.py
  ```

  This is handy for ad-hoc logging or testing when the service is already running.

## Home Assistant Integration

Full documentation and ready-to-use configuration examples live in
[`homeassistant/README.md`](homeassistant/README.md).

### Quick start

Two integration approaches are available – use one or both:

#### SQL sensors (direct database access)

Home Assistant's built-in [SQL integration](https://www.home-assistant.io/integrations/sql/)
can query the SQLite database directly.  Mount the `data/` directory into the
HA container (see `docker-compose.yml`) and add the following to your
`configuration.yaml`:

```yaml
sql:
  - name: "Pool Guest Count"
    db_url: sqlite:////data/guest_logs.db
    query: >
      SELECT count FROM guest_logs
      WHERE pool_uid = 'SSD-4'
      ORDER BY recorded_at DESC LIMIT 1
    column: "count"
    unit_of_measurement: "guests"
    state_class: "measurement"
```

`state_class: "measurement"` enables Home Assistant's **long-term statistics**
so historical data is retained even after the recorder purges raw history, and
the `statistics-graph` Lovelace card works out of the box.

See [`homeassistant/configuration.yaml.example`](homeassistant/configuration.yaml.example)
for the full set of sensors (occupancy %, today's average, peak, 7-day stats).

#### REST sensors (API-based)

If HA cannot access the database file directly, poll the FastAPI endpoints instead:

```yaml
rest:
  - resource: "http://pool-guest-logger:8000/api/latest"
    scan_interval: 300
    sensor:
      - name: "Pool Guests"
        value_template: "{{ value_json.count }}"
        unit_of_measurement: "guests"
        state_class: "measurement"
```

#### Schedule logging from HA

```yaml
rest_command:
  pool_guest_log:
    url: "http://pool-guest-logger:8000/api/log"
    method: post

automation:
  - alias: "Log pool guests every 10 minutes"
    trigger:
      - platform: time_pattern
        minutes: "/10"
    action:
      - service: rest_command.pool_guest_log
```

See [`homeassistant/automations.yaml.example`](homeassistant/automations.yaml.example)
for occupancy alerts and quiet-time notifications.

#### Dashboard

```yaml
type: statistics-graph
title: Guest Count – This Week
entities:
  - sensor.pool_guest_count
days_to_show: 7
period: day
stat_types: [mean, max, min]
```

See [`homeassistant/lovelace-card.yaml.example`](homeassistant/lovelace-card.yaml.example)
for gauge cards, history graphs, and a Markdown summary card.

#### Running both services with Docker Compose

Uncomment the `homeassistant` service block in `docker-compose.yml` to run
Home Assistant alongside the pool logger.  The database is mounted read-only
into the HA container to prevent SQLite locking issues.

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
