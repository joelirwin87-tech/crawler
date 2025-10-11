"""Lightweight SQLite helpers for the trending product bot."""
from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Mapping, MutableMapping, Optional

from config import DATABASE_PATH

Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection(path: Path | str = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(path: Path | str = DATABASE_PATH) -> None:
    """Ensure the database schema exists."""
    with get_connection(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                image_url TEXT,
                description TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                trend_score REAL NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                reviews INTEGER,
                rating REAL,
                orders INTEGER,
                votes INTEGER,
                price REAL,
                comments INTEGER,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_product ON metrics(product_id, captured_at DESC)"
        )
        conn.commit()


def upsert_product(product: Mapping[str, object], *, conn: sqlite3.Connection) -> int:
    """Insert or update a product row and return its id."""
    now = datetime.utcnow().isoformat()
    existing = conn.execute(
        "SELECT id FROM products WHERE url = ?",
        (str(product["url"]),),
    ).fetchone()

    if existing:
        product_id = int(existing["id"])
        conn.execute(
            """
            UPDATE products
            SET name = ?, platform = ?, image_url = ?, description = ?, trend_score = ?, last_seen = ?
            WHERE id = ?
            """,
            (
                product.get("name"),
                product.get("platform"),
                product.get("image_url"),
                product.get("description"),
                float(product.get("trend_score", 0)),
                now,
                product_id,
            ),
        )
        return product_id

    cursor = conn.execute(
        """
        INSERT INTO products (name, platform, url, image_url, description, first_seen, last_seen, trend_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product.get("name"),
            product.get("platform"),
            product.get("url"),
            product.get("image_url"),
            product.get("description"),
            now,
            now,
            float(product.get("trend_score", 0)),
        ),
    )
    return int(cursor.lastrowid)


def add_metric(product_id: int, metrics: Mapping[str, object], *, conn: sqlite3.Connection) -> None:
    """Persist a metrics snapshot for a product."""
    conn.execute(
        """
        INSERT INTO metrics (product_id, captured_at, reviews, rating, orders, votes, price, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            metrics.get("captured_at", datetime.utcnow().isoformat()),
            _safe_int(metrics.get("reviews")),
            _safe_float(metrics.get("rating")),
            _safe_int(metrics.get("orders")),
            _safe_int(metrics.get("votes")),
            _safe_float(metrics.get("price")),
            _safe_int(metrics.get("comments")),
        ),
    )


def record_products(products: Iterable[MutableMapping[str, object]], path: Path | str = DATABASE_PATH) -> None:
    """Persist a collection of product payloads and associated metrics."""
    with get_connection(path) as conn:
        for payload in products:
            metrics = payload.get("metrics", {})
            product_fields = {k: v for k, v in payload.items() if k != "metrics"}
            product_id = upsert_product(product_fields, conn=conn)
            if metrics:
                metrics.setdefault("captured_at", datetime.utcnow().isoformat())
                add_metric(product_id, metrics, conn=conn)
        conn.commit()


def fetch_products(path: Path | str = DATABASE_PATH) -> List[sqlite3.Row]:
    """Return all products with their latest metrics snapshot."""
    with get_connection(path) as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.platform, p.url, p.image_url, p.description,
                   p.first_seen, p.last_seen, p.trend_score,
                   m.reviews, m.rating, m.orders, m.votes, m.price, m.comments, m.captured_at
            FROM products AS p
            LEFT JOIN metrics AS m ON m.id = (
                SELECT id FROM metrics WHERE product_id = p.id ORDER BY captured_at DESC, id DESC LIMIT 1
            )
            ORDER BY p.last_seen DESC
            """
        ).fetchall()
    return list(rows)


def fetch_metrics_for_product(product_id: int, *, limit: int = 30, path: Path | str = DATABASE_PATH) -> List[sqlite3.Row]:
    with get_connection(path) as conn:
        rows = conn.execute(
            """
            SELECT captured_at, reviews, rating, orders, votes, price, comments
            FROM metrics
            WHERE product_id = ?
            ORDER BY captured_at ASC
            LIMIT ?
            """,
            (product_id, limit),
        ).fetchall()
    return list(rows)


def export_products_to_csv(file_obj, path: Path | str = DATABASE_PATH) -> None:
    """Write product data and latest metrics to a CSV file-like object."""
    rows = fetch_products(path)
    if not rows:
        return

    writer = csv.writer(file_obj)
    writer.writerow(
        [
            "id",
            "name",
            "platform",
            "url",
            "trend_score",
            "reviews",
            "rating",
            "orders",
            "votes",
            "price",
            "comments",
            "first_seen",
            "last_seen",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["name"],
                row["platform"],
                row["url"],
                row["trend_score"],
                row["reviews"],
                row["rating"],
                row["orders"],
                row["votes"],
                row["price"],
                row["comments"],
                row["first_seen"],
                row["last_seen"],
            ]
        )


def _safe_int(value: object | None) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(value: object | None) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
