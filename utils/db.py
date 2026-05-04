import logging
import os
import time
from contextlib import contextmanager

import pymysql
from fastapi import HTTPException

from utils.config import CACHE_TTL

logger = logging.getLogger(__name__)

_cache: dict = {}


def get_db():
    """Open and return a new pymysql connection using credentials from the environment."""
    return pymysql.connect(
        host=os.environ["SQL_HOST"],
        user=os.environ["SQL_USER"],
        password=os.environ["SQL_PASSWD"],
        database=os.environ["SQL_DB"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
    )


@contextmanager
def db_conn():
    """Yield a DB connection, handling open/close and mapping failures to 503."""
    conn = None
    try:
        conn = get_db()
        yield conn
    except HTTPException:
        raise
    except Exception as e:
        logger.error("DB connection failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def query_one(conn, sql, params):
    """Execute a query and return the first matching row as a dict, or None."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("DB query failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Database query failed: {e}")


def query_all(conn, sql, params):
    """Execute a query and return all matching rows as a list of dicts."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("DB query failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Database query failed: {e}")


def cache_get(key):
    """Return cached data for key if it exists and hasn't expired, otherwise None."""
    cached = _cache.get(key)
    if cached and time.monotonic() - cached["at"] < CACHE_TTL:
        return cached["data"]
    return None


def cache_set(key, data):
    """Store data in the cache under key, timestamped for TTL expiry."""
    _cache[key] = {"at": time.monotonic(), "data": data}
