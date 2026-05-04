import time
from fastapi import APIRouter, HTTPException, Security, Query
from utils.auth import require_api_key
from utils.config import HOURLY_TABLE, DAILY_TABLE
from utils.db import db_conn, query_one, query_all, cache_get, cache_set
from utils.log import logger
from utils.units import n, to_f, to_mph

router = APIRouter()


def _validate_units(units: str):
    """Raise 400 if the units parameter is not 'metric' or 'imperial'."""
    if units not in ("metric", "imperial"):
        raise HTTPException(status_code=400, detail="units must be 'metric' or 'imperial'")


def build_daily_row(row, imperial: bool) -> dict:
    """Build a single daily forecast dict from a DB row, converting units as requested."""
    return {
        "day_start":          row["day_start_local"],
        "condition":          n(row["conditions"], ""),
        "icon":               n(row["icon"], ""),
        "high_f" if imperial else "high_c": to_f(row["air_temp_high"]) if imperial else n(row["air_temp_high"]),
        "low_f"  if imperial else "low_c":  to_f(row["air_temp_low"])  if imperial else n(row["air_temp_low"]),
        "precip_probability": n(row["precip_probability"]),
        "precip_type":        n(row["precip_type"], ""),
        "sunrise":            row["sunrise"],
        "sunset":             row["sunset"],
    }


def build_hourly_row(row, imperial: bool) -> dict:
    """Build a single hourly forecast dict from a DB row, converting units as requested."""
    return {
        "forecast_time":       row["forecast_time"],
        "condition":           n(row["conditions"], ""),
        "icon":                n(row["icon"], ""),
        "temp_f" if imperial else "temp_c":               to_f(row["air_temperature"]) if imperial else n(row["air_temperature"]),
        "feels_like_f" if imperial else "feels_like_c":   to_f(row["feels_like"]) if imperial else n(row["feels_like"]),
        "wind_speed":          to_mph(row["wind_avg"]) if imperial else n(row["wind_avg"]),
        "wind_unit":           "mph" if imperial else "m/s",
        "wind_direction_deg":  n(row["wind_direction"]),
        "wind_direction_card": n(row["wind_direction_cardinal"], ""),
        "precip_probability":  n(row["precip_probability"]),
        "precip_type":         n(row["precip_type"], ""),
        "humidity_pct":        n(row["relative_humidity"]),
        "uv_index":            n(row["uv"]),
    }

@router.get("/weather/forecast/daily")
def forecast_daily(
    station_id: int = Query(..., description="Tempest station ID"),
    units: str = Query("metric", description="metric or imperial"),
    days: int = Query(2, ge=1, le=10, description="Number of days to return"),
    _: str = Security(require_api_key),
):
    _validate_units(units)
    imperial = units == "imperial"
    cache_key = ("daily", station_id, imperial)

    if (data := cache_get(cache_key)) is not None:
        logger.debug("Cache hit — daily forecast station=%s", station_id)
        return data

    logger.info("DB fetch — daily forecast station=%s days=%s", station_id, days)
    with db_conn() as conn:
        latest_fetch = query_one(conn,
            f"SELECT MAX(fetched_at) AS fa FROM `{DAILY_TABLE}` WHERE station_id = %s",
            (station_id,))
        if not latest_fetch or not latest_fetch["fa"]:
            logger.warning("No daily forecast found for station=%s", station_id)
            raise HTTPException(status_code=404, detail=f"No forecast found for station {station_id}")

        rows = query_all(conn,
            f"SELECT * FROM `{DAILY_TABLE}` WHERE station_id = %s AND fetched_at = %s "
            "ORDER BY day_start_local ASC LIMIT %s",
            (station_id, latest_fetch["fa"], days))

    data = [build_daily_row(r, imperial) for r in rows]
    cache_set(cache_key, data)
    return data

@router.get("/weather/forecast/hourly")
def forecast_hourly(
    station_id: int = Query(..., description="Tempest station ID"),
    units: str = Query("metric", description="metric or imperial"),
    hours: int = Query(24, ge=1, le=48, description="Number of hours to return"),
    _: str = Security(require_api_key),
):
    _validate_units(units)
    imperial = units == "imperial"
    cache_key = ("hourly", station_id, imperial)

    if (data := cache_get(cache_key)) is not None:
        logger.debug("Cache hit — hourly forecast station=%s", station_id)
        return data

    logger.info("DB fetch — hourly forecast station=%s hours=%s", station_id, hours)
    with db_conn() as conn:
        latest_fetch = query_one(conn,
            f"SELECT MAX(fetched_at) AS fa FROM `{HOURLY_TABLE}` WHERE station_id = %s",
            (station_id,))
        if not latest_fetch or not latest_fetch["fa"]:
            logger.warning("No hourly forecast found for station=%s", station_id)
            raise HTTPException(status_code=404, detail=f"No forecast found for station {station_id}")

        now = int(time.time())
        rows = query_all(conn,
            f"SELECT * FROM `{HOURLY_TABLE}` WHERE station_id = %s AND fetched_at = %s "
            "AND forecast_time >= %s ORDER BY forecast_time ASC LIMIT %s",
            (station_id, latest_fetch["fa"], now, hours))

    data = [build_hourly_row(r, imperial) for r in rows]
    cache_set(cache_key, data)
    return data