# Weather API

A read-only JSON API serving live observations and forecasts from a WeatherFlow Tempest station. Data is sourced from a mariadb database populated by tempest_collector.

## Authentication

All endpoints (except `/v1/weather/health`) require an API key passed as a request header.

```
X-API-Key: wapi_<key>
```

Keys are generated using `keygen.py` and stored hashed in the database. An invalid or missing key returns `401`.

---

## Endpoints

### Health check

```
GET /v1/weather/health
```

No authentication required. Returns `200` if the service is running.

```json
{"status": "ok"}
```

---

### Latest observation

```
GET /v1/weather/latest
```

Returns the most recent sensor reading for a station.

**Query parameters**

| Parameter  | Type   | Required | Default  | Description                    |
|------------|--------|----------|----------|--------------------------------|
| station_id | int    | yes      | —        | Tempest station ID             |
| units      | string | no       | `metric` | `metric` or `imperial`         |

**Example**

```
GET /v1/weather/latest?station_id=12345&units=imperial
X-API-Key: wapi_<key>
```

**Response**

```json
{
  "station_id": 12345,
  "timestamp": 1743200000,
  "units": "imperial",
  "condition": "Clear",
  "icon": "clear-day",
  "temperature": {
    "air_f": 72.3,
    "feels_like_f": 70.1,
    "dew_point_f": 55.4,
    "humidity_pct": 54,
    "heat_index_f": 71.8,
    "wind_chill_f": null
  },
  "pressure": {
    "station_inhg": 29.92,
    "sea_level_inhg": 30.01,
    "trend": "steady"
  },
  "wind": {
    "avg_mph": 5.4,
    "gust_mph": 9.2,
    "lull_mph": 1.1,
    "direction_deg": 225,
    "direction_card": "SW"
  },
  "precipitation": {
    "last_minute_in": 0.0,
    "last_1hr_in": 0.0,
    "today_in": 0.12
  },
  "solar": {
    "radiation_wm2": 320,
    "uv_index": 3.2,
    "brightness_lux": 28000
  },
  "lightning": {
    "last_minute": 0,
    "last_1hr": 0,
    "last_3hr": 2,
    "last_distance_km": 18
  }
}
```

Metric response uses `_c`, `_mbar`, `_ms`, and `_mm` suffixed keys in place of their imperial equivalents.

---

### Display (e-ink summary)

```
GET /v1/weather/display
```

A trimmed response designed for resource-constrained clients (e.g. ESP32 e-ink displays). Combines the latest observation with the current and next day's forecast.

**Query parameters**

| Parameter  | Type   | Required | Default    | Description            |
|------------|--------|----------|------------|------------------------|
| station_id | int    | yes      | —          | Tempest station ID     |
| units      | string | no       | `imperial` | `metric` or `imperial` |

**Response**

```json
{
  "station_id": 12345,
  "timestamp": 1743200000,
  "stale": false,
  "units": "imperial",
  "current": {
    "condition": "Clear",
    "icon": "clear-day",
    "temp_f": 72.3,
    "feels_like_f": 70.1,
    "humidity_pct": 54,
    "wind_mph": 5.4,
    "wind_card": "SW",
    "uv_index": 3.2,
    "lightning_1hr": 0,
    "lightning_dist_km": 18
  },
  "today": {
    "condition": "Partly Cloudy",
    "icon": "partly-cloudy-day",
    "high_f": 78.0,
    "low_f": 61.0,
    "precip_probability": 10,
    "uv_index": 5.1,
    "sunrise": 1743170400,
    "sunset": 1743216000
  },
  "tomorrow": {
    "condition": "Rain",
    "icon": "rain",
    "high_f": 65.0,
    "low_f": 55.0,
    "precip_probability": 80,
    "uv_index": 1.0
  }
}
```

`stale` is `true` if the most recent observation is older than the configured stale threshold (default 5 minutes). `sunrise`/`sunset` are Unix epoch seconds.

---

### Daily forecast

```
GET /v1/weather/forecast/daily
```

Returns daily forecast rows from the latest forecast snapshot.

**Query parameters**

| Parameter  | Type   | Required | Default  | Description                  |
|------------|--------|----------|----------|------------------------------|
| station_id | int    | yes      | —        | Tempest station ID           |
| units      | string | no       | `metric` | `metric` or `imperial`       |
| days       | int    | no       | `2`      | Number of days to return (1–10) |

**Response**

```json
[
  {
    "day_start": 1743120000,
    "condition": "Partly Cloudy",
    "icon": "partly-cloudy-day",
    "high_f": 78.0,
    "low_f": 61.0,
    "precip_probability": 10,
    "precip_type": "rain",
    "sunrise": 1743170400,
    "sunset": 1743216000
  }
]
```

---

### Hourly forecast

```
GET /v1/weather/forecast/hourly
```

Returns hourly forecast rows from the latest forecast snapshot, starting from the current hour.

**Query parameters**

| Parameter  | Type   | Required | Default  | Description                    |
|------------|--------|----------|----------|--------------------------------|
| station_id | int    | yes      | —        | Tempest station ID             |
| units      | string | no       | `metric` | `metric` or `imperial`         |
| hours      | int    | no       | `24`     | Number of hours to return (1–48) |

**Response**

```json
[
  {
    "forecast_time": 1743200000,
    "condition": "Clear",
    "icon": "clear-day",
    "temp_f": 72.0,
    "feels_like_f": 70.0,
    "wind_speed": 5.4,
    "wind_unit": "mph",
    "wind_direction_deg": 225,
    "wind_direction_card": "SW",
    "precip_probability": 5,
    "precip_type": "rain",
    "humidity_pct": 54,
    "uv_index": 3.0
  }
]
```

`wind_unit` is `mph` for imperial or `m/s` for metric.

---

## Rate limiting

Requests are limited to **60 per minute per API key** using a sliding window. The limit is evaluated per key, not per IP.

Every response includes the following headers:

| Header                  | Description                              |
|-------------------------|------------------------------------------|
| `X-RateLimit-Limit`     | Maximum requests allowed per window      |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset`     | Window duration in seconds (60)          |

When the limit is exceeded the API returns `429` with a `Retry-After` header indicating how many seconds to wait before retrying. The block clears automatically as requests age out of the 60-second window — there is no fixed block duration.

```
HTTP/1.1 429 Too Many Requests
Retry-After: 12
```

```json
{"detail": "Rate limit exceeded"}
```

The default limit of 60 requests/minute is configurable via the `RATE_LIMIT` environment variable.

---

## Error responses

| Status | Meaning                                        |
|--------|------------------------------------------------|
| 400    | Invalid parameter (e.g. unknown `units` value) |
| 401    | Missing or invalid API key                     |
| 404    | No data found for the given `station_id`       |
| 429    | Rate limit exceeded — check `Retry-After`      |
| 503    | Database unavailable                           |

All errors return a JSON body:

```json
{"detail": "error description"}
```

---

## Caching

Responses are cached in memory per `(endpoint, station_id, units)`. The default TTL is 60 seconds, configurable via the `CACHE_TTL` environment variable.
