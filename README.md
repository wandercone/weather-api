# weather-api

A read-only FastAPI service that exposes live observations and forecasts from a WeatherFlow Tempest station. Data is read from a mariadb database populated by the tempest_collector.

## Features

- Current conditions, display summary, and hourly/daily forecasts
- Metric and imperial unit support
- API key authentication with per-key rate limiting (60 req/min, sliding window)
- In-memory response caching (60s TTL)
- Stale data detection
- Structured request logging

## Requirements

- Python 3.12+
- MySQL database populated by the Tempest collector
- SWAG (or any reverse proxy) for SSL termination

## Setup

### 1. Database

Run the schema against your MySQL instance to create the `api_keys` table:

```bash
mysql -u <user> -p <database> < db/api_keys.sql
```

### 2. Environment

Copy `.env` and fill in your values:

```bash
cp .env .env.local
```

| Variable           | Required | Default                   | Description                          |
|--------------------|----------|---------------------------|--------------------------------------|
| `SQL_HOST`         | yes      | —                         | MySQL host                           |
| `SQL_USER`         | yes      | —                         | MySQL user                           |
| `SQL_PASSWD`       | yes      | —                         | MySQL password                       |
| `SQL_DB`           | yes      | —                         | MySQL database name                  |
| `OBS_TABLE`        | no       | `weather_observations`    | Observations table name              |
| `HOURLY_TABLE`     | no       | `weather_forecast_hourly` | Hourly forecast table name           |
| `DAILY_TABLE`      | no       | `weather_forecast_daily`  | Daily forecast table name            |
| `CACHE_TTL`        | no       | `60`                      | Response cache TTL in seconds        |
| `STALE_THRESHOLD`  | no       | `300`                     | Seconds before an observation is considered stale |
| `RATE_LIMIT`       | no       | `60`                      | Max requests per minute per API key  |

### 3. Generate an API key

```bash
python keygen.py "my client"              # no expiry
python keygen.py "temp client" --expires 30d
python keygen.py "short-lived" --expires 24h
```

The generated key (prefixed `wapi_`) is printed once and cannot be recovered. Store it securely.

### 4. Run

**Direct:**

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Docker:**

```bash
docker compose up -d
```

## API

See [API.md](API.md) for the full reference.

Quick summary:

| Method | Path                          | Description              |
|--------|-------------------------------|--------------------------|
| GET    | `/v1/weather/health`          | Health check (no auth)   |
| GET    | `/v1/weather/latest`          | Latest observation       |
| GET    | `/v1/weather/display`         | E-ink display summary    |
| GET    | `/v1/weather/forecast/daily`  | Daily forecast           |
| GET    | `/v1/weather/forecast/hourly` | Hourly forecast          |

All data endpoints require `X-API-Key: wapi_<key>`.

## Reverse proxy

The service expects to sit behind a reverse proxy that handles SSL. Nginx location block example:

```nginx
location /v1/weather/ {
    include /config/nginx/proxy.conf;
    include /config/nginx/resolver.conf;
    set $upstream_app <host>;
    set $upstream_port 8000;
    set $upstream_proto http;
    proxy_pass $upstream_proto://$upstream_app:$upstream_port;
}
```
