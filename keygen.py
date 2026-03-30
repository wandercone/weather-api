#!/usr/bin/env python3
"""Generate and register a new API key in the api_keys table.

Usage:
    python keygen.py <label> [--expires DURATION]

Duration examples: 30d, 24h, 2w, 90d

The generated key is printed once and cannot be recovered — store it securely.
"""
import argparse
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta

import pymysql
from dotenv import load_dotenv

load_dotenv()

KEY_PREFIX = "wapi_"


def _hash_to_uuid(hex_hash: str) -> str:
    h = hex_hash[:32]
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
_DURATION_RE = re.compile(r"^(\d+)(h|d|w)$")
_DURATION_UNITS = {"h": "hours", "d": "days", "w": "weeks"}


def parse_duration(value: str) -> timedelta:
    m = _DURATION_RE.match(value.strip().lower())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid duration '{value}'. Use a number followed by h, d, or w (e.g. 30d, 24h, 2w)."
        )
    amount, unit = int(m.group(1)), m.group(2)
    return timedelta(**{_DURATION_UNITS[unit]: amount})


def main():
    parser = argparse.ArgumentParser(description="Generate and register a new API key.")
    parser.add_argument("label", help="Human-readable label for this key")
    parser.add_argument(
        "--expires",
        metavar="DURATION",
        type=parse_duration,
        default=None,
        help="Optional expiry duration, e.g. 30d, 24h, 2w (default: no expiry)",
    )
    args = parser.parse_args()

    label = args.label.strip()
    if not label:
        parser.error("label cannot be empty")

    expires_at = datetime.now() + args.expires if args.expires else None

    key = KEY_PREFIX + secrets.token_hex(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    key_id = _hash_to_uuid(key_hash)

    conn = pymysql.connect(
        host=os.environ["SQL_HOST"],
        user=os.environ["SQL_USER"],
        password=os.environ["SQL_PASSWD"],
        database=os.environ["SQL_DB"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO api_keys (id, key_hash, label, expires_at) VALUES (%s, %s, %s, %s)",
                (key_id, key_hash, label, expires_at),
            )
        conn.commit()
    finally:
        conn.close()

    print(f"\nAPI key created for '{label}':")
    print(f"\n  {key}\n")
    if expires_at:
        print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M')} (local)")
    else:
        print("Expires: never")
    print("\nStore this key securely — it cannot be recovered.")


if __name__ == "__main__":
    main()
