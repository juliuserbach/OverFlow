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

- **Trigger logging on a schedule**
  1. Define a `rest_command` that POSTs to the API:

     ```yaml
     rest_command:
       pool_guest_log:
         url: "http://127.0.0.1:8000/api/log"
         method: post
     ```

  2. Create an automation that runs every _n_ minutes (adjust `/15` as needed):

     ```yaml
     automation:
       - alias: "Log pool guests every 15 minutes"
         trigger:
           - platform: time_pattern
             minutes: "/15"
         action:
           - service: rest_command.pool_guest_log
     ```

- **Expose the latest values as sensors**

  ```yaml
  rest:
    - resource: "http://127.0.0.1:8000/api/latest"
      method: GET
      scan_interval: 300  # seconds
      sensor:
        name: "Pool Guests"
        value_template: "{{ value_json.count }}"
        unit_of_measurement: "guests"
        json_attributes:
          - capacity
          - recorded_at
  ```

- **Add a Lovelace visualization**
  - Native history graph:

    ```yaml
    type: history-graph
    entities:
      - sensor.pool_guests
    hours_to_show: 24
    refresh_interval: 60
    ```

  - (Optional) [ApexCharts](https://github.com/RomRider/apexcharts-card) card for more control:

    ```yaml
    type: custom:apexcharts-card
    graph_span: 24h
    update_interval: 5min
    series:
      - entity: sensor.pool_guests
        name: Gäste
    ```

- Embed the built-in dashboard as an iframe using the [Webpage card](https://www.home-assistant.io/lovelace/iframe/) pointed at the FastAPI URL if you prefer the project’s UI.

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
