# Home Assistant Integration

This directory contains ready-to-use example configuration files for integrating
**OverFlow – Pool Guest Logger** with [Home Assistant](https://www.home-assistant.io/).

## Overview

Two complementary integration approaches are provided:

| Approach | How it works | Best for |
|----------|--------------|----------|
| **SQL sensor** | HA queries the SQLite database directly via SQLAlchemy | Same host or shared Docker volume |
| **REST sensor** | HA polls the FastAPI endpoints over HTTP | Remote installations or simpler setups |

Both approaches use `state_class: "measurement"` so Home Assistant records
long-term statistics and lets you plot historical graphs out of the box.

---

## Files in this directory

| File | Description |
|------|-------------|
| `configuration.yaml.example` | SQL sensors, REST sensors, template sensors, and `rest_command` |
| `automations.yaml.example` | Scheduled logging, occupancy alerts, quiet-time notifications |
| `lovelace-card.yaml.example` | Dashboard card examples (entities, gauge, history-graph, statistics-graph) |

---

## Prerequisites

- Home Assistant **2022.x** or newer (the SQL integration has been built-in since 2022.x; 2023.x is recommended for the latest statistics features)
- OverFlow running and writing to `guest_logs.db`
- The database file must be **readable** by the Home Assistant process

---

## Step-by-step setup

### 1. Make the database accessible to Home Assistant

#### Docker Compose (recommended)

Mount the `data/` directory from the pool logger as a **read-only** volume in
the Home Assistant container.  The `docker-compose.yml` in the project root
contains a commented-out Home Assistant service – uncomment it:

```yaml
homeassistant:
  image: ghcr.io/home-assistant/home-assistant:stable
  volumes:
    - ./homeassistant/config:/config
    - ./data:/data:ro        # ← read-only access to the pool database
  ports:
    - "8123:8123"
  restart: unless-stopped
  networks:
    - pool-network
```

Inside HA, the database is then available at `/data/guest_logs.db` and the
SQLAlchemy URL is:

```
sqlite:////data/guest_logs.db
```

(Four slashes: `sqlite://` + `//` + `/data/…`)

#### Home Assistant OS / Supervised

Copy (or symlink) `guest_logs.db` to a path inside the HA configuration
directory, for example `/config/pool/guest_logs.db`, and use:

```
sqlite:////config/pool/guest_logs.db
```

#### Home Assistant Core (venv)

Place the database wherever the HA user can read it and use the matching
absolute path.

### 2. Add the SQL sensors

Copy the `sql:` block from `configuration.yaml.example` into your
`configuration.yaml` (or a package file) and set the correct `pool_uid`.

Available pool UIDs are listed by the `/api/pools` endpoint:

```bash
curl http://your-pool-logger:8000/api/pools
```

### 3. (Optional) Add the REST sensors

If Home Assistant cannot access the database file directly, use the `rest:`
block from `configuration.yaml.example` instead.  Point `resource` at the
OverFlow API:

```
http://pool-guest-logger:8000/api/latest
```

When both services are in the same Docker Compose project you can use the
service name (`pool-guest-logger`) directly.

### 4. Add automations

Copy the relevant automations from `automations.yaml.example` into your
`automations.yaml` or import them via the UI.

Adjust the `minutes: "/10"` trigger to match your desired logging interval.

### 5. Add dashboard cards

Open a Lovelace dashboard, add a **Manual card**, and paste the YAML from
`lovelace-card.yaml.example`.

---

## state_class and long-term statistics

Setting `state_class: "measurement"` on a sensor tells Home Assistant that:

- The value can go up **and** down (unlike `total_increasing` for energy meters).
- The recorder should keep **long-term statistics** (hourly/daily aggregates)
  even after the raw history is pruned.
- The sensor can be used in the **Statistics** and **Energy** dashboards.
- The `statistics-graph` Lovelace card will work with it.

Without `state_class` HA still records the raw values, but the statistics
features are disabled and old data is lost when the recorder purges history.

All numeric sensors in `configuration.yaml.example` already include
`state_class: "measurement"`.

---

## Database access and locking

SQLite supports only one writer at a time.  The pool logger writes to the
database; Home Assistant should only read.

- Always mount the database **read-only** (`:ro`) in Docker.
- If you observe `database is locked` errors, enable WAL mode in the logger:

  ```python
  # In app/database.py, after engine creation:
  with engine.connect() as conn:
      conn.execute(text("PRAGMA journal_mode=WAL"))
  ```

  WAL mode allows concurrent reads while a write is in progress.

---

## Troubleshooting

### Sensor shows `unavailable`

1. Check that the `db_url` path is correct and the file exists.
2. Verify HA has read permission: `ls -la /data/guest_logs.db`
3. Check the Home Assistant logs: **Settings → System → Logs**

### `OperationalError: unable to open database file`

The path inside the container differs from the host path.
- Use `docker exec -it homeassistant ls /data` to confirm the mount.
- Ensure the `data` volume is correctly defined in `docker-compose.yml`.

### `database is locked`

- Use read-only mount (`:ro`) for the HA container.
- Enable WAL mode in the pool logger (see above).

### Data is stale

- Confirm the logging automation is firing (check **Automations → last triggered**).
- Increase `scan_interval` on REST sensors to avoid hammering the API.
- The SQL sensors refresh whenever HA polls them; default is every 30 seconds.

---

## Example useful queries

```sql
-- Latest guest count for a specific pool
SELECT count, capacity, recorded_at, pool_uid
FROM guest_logs
WHERE pool_uid = 'SSD-4'
ORDER BY recorded_at DESC
LIMIT 1;

-- Today's average
SELECT AVG(count) AS avg_count
FROM guest_logs
WHERE DATE(recorded_at) = DATE('now')
  AND pool_uid = 'SSD-4';

-- Peak time today
SELECT count, TIME(recorded_at) AS time
FROM guest_logs
WHERE DATE(recorded_at) = DATE('now')
  AND pool_uid = 'SSD-4'
ORDER BY count DESC
LIMIT 1;

-- Weekly statistics (one row per day)
SELECT
  DATE(recorded_at) AS date,
  AVG(count)        AS avg,
  MAX(count)        AS max,
  MIN(count)        AS min
FROM guest_logs
WHERE recorded_at >= DATE('now', '-7 days')
GROUP BY DATE(recorded_at)
ORDER BY date DESC;
```
