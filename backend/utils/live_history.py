"""SQLite storage for real price observations collected from live feeds."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "price_history.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            website TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            product_link TEXT,
            observed_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_obs_name_date ON price_observations(product_name, observed_at)"
    )
    conn.commit()
    return conn


def record_observations(rows: Iterable[dict]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    conn = _connect()
    inserted = 0
    try:
        for row in rows:
            try:
                price = float(row.get("price"))
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue
            conn.execute(
                """
                INSERT INTO price_observations
                    (product_name, website, price, currency, product_link, observed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("product_name") or "N/A"),
                    str(row.get("website") or "Unknown"),
                    price,
                    str(row.get("currency") or "INR"),
                    str(row.get("product_link") or "#"),
                    str(row.get("observed_at") or row.get("date") or ""),
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def history_for_product(product_name: str, limit: int = 120) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT product_name, website, price, currency, product_link, observed_at
            FROM price_observations
            WHERE lower(product_name) = lower(?) AND currency = 'INR'
            ORDER BY observed_at ASC
            LIMIT ?
            """,
            (product_name, max(1, min(int(limit), 500))),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def stats() -> dict:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS observations, MAX(observed_at) AS last_observed FROM price_observations"
        ).fetchone()
        return {
            "observations": int(row["observations"] or 0),
            "last_observed": row["last_observed"],
            "database": str(DB_PATH),
        }
    finally:
        conn.close()
