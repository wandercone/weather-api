import os
from utils.log import logger

_REQUIRED = ["SQL_HOST", "SQL_USER", "SQL_PASSWD", "SQL_DB"]
_missing = [v for v in _REQUIRED if not os.getenv(v)]
if _missing:
    for var in _missing:
        logger.critical("Missing required environment variable: %s", var)
    raise SystemExit(1)

OBS_TABLE       = os.getenv("OBS_TABLE",       "weather_observations")
HOURLY_TABLE    = os.getenv("HOURLY_TABLE",    "weather_forecast_hourly")
DAILY_TABLE     = os.getenv("DAILY_TABLE",     "weather_forecast_daily")
CACHE_TTL       = int(os.getenv("CACHE_TTL",        "60"))
STALE_THRESHOLD = int(os.getenv("STALE_THRESHOLD", "300"))
RATE_LIMIT      = int(os.getenv("RATE_LIMIT",       "60"))  # requests per minute per key
