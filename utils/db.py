import os
import time
import pymysql
from utils.config import CACHE_TTL

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
    )

def query_one(conn, sql, params):
    """Execute a query and return the first matching row as a dict, or None."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()

def query_all(conn, sql, params):
    """Execute a query and return all matching rows as a list of dicts."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def cache_get(key):
    """Return cached data for key if it exists and hasn't expired, otherwise None."""
    cached = _cache.get(key)
    if cached and time.monotonic() - cached["at"] < CACHE_TTL:
        return cached["data"]
    return None

def cache_set(key, data):
    """Store data in the cache under key, timestamped for TTL expiry."""
    _cache[key] = {"at": time.monotonic(), "data": data}
