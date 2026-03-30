import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

logging.getLogger("uvicorn.access").disabled = True

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware  # noqa: E402
from utils.log import logger  # noqa: E402
from utils.config import OBS_TABLE, DAILY_TABLE, HOURLY_TABLE, CACHE_TTL, STALE_THRESHOLD, RATE_LIMIT  # noqa: E402
from routes.weather import router as weather_router  # noqa: E402
from routes.forecast import router as forecast_router  # noqa: E402

_rate_store: dict = defaultdict(list)
_RATE_WINDOW = 60  # seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Weather API starting — obs=%s daily=%s hourly=%s cache_ttl=%ss stale_threshold=%ss rate_limit=%s/min",
        OBS_TABLE, DAILY_TABLE, HOURLY_TABLE, CACHE_TTL, STALE_THRESHOLD, RATE_LIMIT,
    )
    yield

app = FastAPI(title="Weather API", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="10.253.100.1")

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path != "/v1/weather/health":
        key = request.headers.get("x-api-key") or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        window_start = now - _RATE_WINDOW
        timestamps = [t for t in _rate_store[key] if t > window_start]
        _rate_store[key] = timestamps

        remaining = RATE_LIMIT - len(timestamps)
        if remaining <= 0:
            retry_after = int(_RATE_WINDOW - (now - timestamps[0])) + 1
            logger.warning("Rate limit exceeded — key=%s", key[:12] + "…" if len(key) > 12 else key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        _rate_store[key].append(now)
        remaining -= 1

    response = await call_next(request)

    if request.url.path != "/v1/weather/health":
        response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"]     = str(_RATE_WINDOW)
        client = request.client.host if request.client else "unknown"
        logger.info("%s %s — %s — %s", request.method, request.url.path, response.status_code, client)

    return response

@app.get("/v1/weather/health")
def health():
    return {"status": "ok"}

app.include_router(weather_router, prefix="/v1")
app.include_router(forecast_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)