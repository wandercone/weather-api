import hashlib
import os

from fastapi import HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader

from utils.db import db_conn
from utils.log import logger

KEY_PREFIX = "wapi_"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def require_api_key(request: Request, key: str = Security(api_key_header)):
    """FastAPI dependency that validates X-API-Key against the api_keys table. Raises 401 on failure."""
    client = request.client.host if request.client else "unknown"

    if not key or not key.startswith(KEY_PREFIX):
        logger.warning("Unauthorized request from %s", client)
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    key_hash = _hash_key(key)

    with db_conn() as conn:
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
        except HTTPException:
            raise
        except Exception as e:
            logger.error("DB query failed during auth: %s", e)
            raise HTTPException(status_code=503, detail="Service unavailable")

    return key
