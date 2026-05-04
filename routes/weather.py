import time
from fastapi import APIRouter, HTTPException, Security, Query
from utils.auth import require_api_key
from utils.config import OBS_TABLE, DAILY_TABLE, STALE_THRESHOLD
from utils.db import db_conn, query_one, query_all, cache_get, cache_set
from utils.log import logger
from utils.units import n, to_f, to_mph, to_inches, to_inhg

router = APIRouter()

def _validate_units(units: str):
    """Raise 400 if the units parameter is not 'metric' or 'imperial'."""
    if units not in ("metric", "imperial"):
        raise HTTPException(status_code=400, detail="units must be 'metric' or 'imperial'")

def build_obs_response(row, imperial: bool) -> dict:
    """Build the full observation response dict from a DB row, converting units as requested."""
    if imperial:
        temperature = {
            "air_f":        to_f(row["air_temperature"]),
            "feels_like_f": to_f(row["feels_like"]),
            "dew_point_f":  to_f(row["dew_point"]),
            "humidity_pct": n(row["relative_humidity"]),
            "heat_index_f": to_f(row["heat_index"]),
            "wind_chill_f": to_f(row["wind_chill"]),
        }
        wind = {
            "avg_mph":        to_mph(row["wind_avg"]),
            "gust_mph":       to_mph(row["wind_gust"]),
            "lull_mph":       to_mph(row["wind_lull"]),
            "direction_deg":  n(row["wind_direction"]),
            "direction_card": n(row["wind_direction_cardinal"], ""),
        }
        pressure = {
            "station_inhg":   to_inhg(row["station_pressure"]),
            "sea_level_inhg": to_inhg(row["sea_level_pressure"]),
            "trend":          n(row["pressure_trend"], "steady"),
        }
        precipitation = {
            "last_minute_in": to_inches(row["precip"]),
            "last_1hr_in":    to_inches(row["precip_accum_last_1hr"]),
            "today_in":       to_inches(row["precip_accum_local_day_final"] or row["precip_accum_local_day"]),
        }
    else:
        temperature = {
            "air_c":        n(row["air_temperature"]),
            "feels_like_c": n(row["feels_like"]),
            "dew_point_c":  n(row["dew_point"]),
            "humidity_pct": n(row["relative_humidity"]),
            "heat_index_c": n(row["heat_index"]),
            "wind_chill_c": n(row["wind_chill"]),
        }
        wind = {
            "avg_ms":         n(row["wind_avg"]),
            "gust_ms":        n(row["wind_gust"]),
            "lull_ms":        n(row["wind_lull"]),
            "direction_deg":  n(row["wind_direction"]),
            "direction_card": n(row["wind_direction_cardinal"], ""),
        }
        pressure = {
            "station_mbar":   n(row["station_pressure"]),
            "sea_level_mbar": n(row["sea_level_pressure"]),
            "trend":          n(row["pressure_trend"], "steady"),
        }
        precipitation = {
            "last_minute_mm": n(row["precip"]),
            "last_1hr_mm":    n(row["precip_accum_last_1hr"]),
            "today_mm":       n(row["precip_accum_local_day_final"] or row["precip_accum_local_day"]),
        }

    return {
        "station_id":    row["station_id"],
        "timestamp":     row["timestamp"],
        "units":         "imperial" if imperial else "metric",
        "condition":     n(row["conditions"], ""),
        "icon":          n(row["icon"], ""),
        "temperature":   temperature,
        "pressure":      pressure,
        "wind":          wind,
        "precipitation": precipitation,
        "solar": {
            "radiation_wm2":  n(row["solar_radiation"]),
            "uv_index":       n(row["uv"]),
            "brightness_lux": n(row["brightness"]),
        },
        "lightning": {
            "last_minute":      n(row["lightning_strike_count"]),
            "last_1hr":         n(row["lightning_strike_count_last_1hr"]),
            "last_3hr":         n(row["lightning_strike_count_last_3hr"]),
            "last_distance_km": n(row["lightning_strike_last_distance"]),
        },
    }

def build_display_response(obs, daily_rows, imperial: bool) -> dict:
    """Build the trimmed display response for the ESP32 e-ink screen from observation and forecast rows."""
    today    = daily_rows[0] if len(daily_rows) > 0 else None
    tomorrow = daily_rows[1] if len(daily_rows) > 1 else None

    age = int(time.time()) - int(obs["timestamp"])
    is_stale = age > STALE_THRESHOLD
    if is_stale:
        logger.warning("Stale data for station=%s — last update %ss ago", obs["station_id"], age)

    def day_block(row, include_sunrise=False):
        if row is None:
            return None
        block = {
            "condition":          n(row["conditions"], ""),
            "icon":               n(row["icon"], ""),
            "high_f" if imperial else "high_c": to_f(row["air_temp_high"]) if imperial else n(row["air_temp_high"]),
            "low_f"  if imperial else "low_c":  to_f(row["air_temp_low"])  if imperial else n(row["air_temp_low"]),
            "precip_probability": n(row["precip_probability"]),
            "uv_index":           n(row.get("uv")),
        }
        if include_sunrise:
            block["sunrise"] = row["sunrise"]
            block["sunset"]  = row["sunset"]
        return block

    return {
        "station_id": obs["station_id"],
        "timestamp":  obs["timestamp"],
        "stale":      is_stale,
        "units":      "imperial" if imperial else "metric",
        "current": {
            "condition":                                     n(obs["conditions"], ""),
            "icon":                                          n(obs["icon"], ""),
            "temp_f"       if imperial else "temp_c":        to_f(obs["air_temperature"]) if imperial else n(obs["air_temperature"]),
            "feels_like_f" if imperial else "feels_like_c":  to_f(obs["feels_like"]) if imperial else n(obs["feels_like"]),
            "humidity_pct":                                  n(obs["relative_humidity"]),
            "wind_mph"     if imperial else "wind_ms":       to_mph(obs["wind_avg"]) if imperial else n(obs["wind_avg"]),
            "wind_card":                                     n(obs["wind_direction_cardinal"], ""),
            "uv_index":                                      n(obs["uv"]),
            "lightning_1hr":                                 n(obs["lightning_strike_count_last_1hr"]),
            "lightning_dist_km":                             n(obs["lightning_strike_last_distance"]),
        },
        "today":    day_block(today,    include_sunrise=True),
        "tomorrow": day_block(tomorrow, include_sunrise=False),
    }

@router.get("/weather/latest")
def latest(
    station_id: int = Query(..., description="Tempest station ID"),
    units: str = Query("metric", description="metric or imperial"),
    _: str = Security(require_api_key),
):
    _validate_units(units)
    imperial = units == "imperial"
    cache_key = ("latest", station_id, imperial)

    if (data := cache_get(cache_key)) is not None:
        logger.debug("Cache hit — latest station=%s", station_id)
        return data

    logger.info("DB fetch — latest station=%s", station_id)
    with db_conn() as conn:
        row = query_one(conn,
            f"SELECT * FROM `{OBS_TABLE}` WHERE station_id = %s ORDER BY timestamp DESC LIMIT 1",
            (station_id,))

    if row is None:
        logger.warning("No observations found for station=%s", station_id)
        raise HTTPException(status_code=404, detail=f"No data found for station {station_id}")

    data = build_obs_response(row, imperial)
    cache_set(cache_key, data)
    return data

@router.get("/weather/display")
def display(
    station_id: int = Query(..., description="Tempest station ID"),
    units: str = Query("imperial", description="metric or imperial"),
    _: str = Security(require_api_key),
):
    _validate_units(units)
    imperial = units == "imperial"
    cache_key = ("display", station_id, imperial)

    if (data := cache_get(cache_key)) is not None:
        logger.debug("Cache hit — display station=%s", station_id)
        return data

    logger.info("DB fetch — display station=%s", station_id)
    with db_conn() as conn:
        obs = query_one(conn,
            f"SELECT * FROM `{OBS_TABLE}` WHERE station_id = %s ORDER BY timestamp DESC LIMIT 1",
            (station_id,))
        if obs is None:
            logger.warning("No observations found for station=%s", station_id)
            raise HTTPException(status_code=404, detail=f"No data found for station {station_id}")

        latest_fetch = query_one(conn,
            f"SELECT MAX(fetched_at) AS fa FROM `{DAILY_TABLE}` WHERE station_id = %s",
            (station_id,))
        daily_rows = []
        if latest_fetch and latest_fetch["fa"]:
            daily_rows = query_all(conn,
                f"SELECT * FROM `{DAILY_TABLE}` WHERE station_id = %s AND fetched_at = %s "
                "ORDER BY day_start_local ASC LIMIT 2",
                (station_id, latest_fetch["fa"]))

    data = build_display_response(obs, daily_rows, imperial)
    cache_set(cache_key, data)
    return data