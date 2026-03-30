import hashlib
import os
import pymysql
from fastapi import HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from utils.log import logger

KEY_PREFIX = "wapi_"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _get_db():
    return pymysql.connect(
        host=os.environ["SQL_HOST"],
        user=os.environ["SQL_USER"],
        password=os.environ["SQL_PASSWD"],
        database=os.environ["SQL_DB"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def require_api_key(request: Request, key: str = Security(api_key_header)):
    """FastAPI dependency that validates X-API-Key against the api_keys table. Raises 401 on failure."""
    client = request.client.host if request.client else "unknown"

    if not key or not key.startswith(KEY_PREFIX):
        logger.warning("Unauthorized request from %s", client)
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    key_hash = _hash_key(key)

    try:
        conn = _get_db()
    except Exception as e:
        logger.error("DB connection failed during auth: %s", e)
        raise HTTPException(status_code=503, detail="Service unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM api_keys "
                "WHERE key_hash = %s AND (expires_at IS NULL OR expires_at > NOW())",
                (key_hash,),
            )
            row = cur.fetchone()

        if row is None:
            logger.warning("Unauthorized request from %s", client)
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

        with conn.cursor() as cur:
            cur.execute("UPDATE api_keys SET last_used_at = NOW() WHERE id = %s", (row["id"],))
        conn.commit()
    finally:
        conn.close()

    return key
