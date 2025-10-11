"""SQLite persistence layer for trending products bot."""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from config import DATA_DIR
from scrapers.base_scraper import ProductRecord

LOGGER = logging.getLogger(__name__)

DB_PATH = DATA_DIR / "trending_products.sqlite3"


@dataclass(slots=True)
class Product:
    id: int
    name: str
    category: Optional[str]
    first_seen: str
    last_updated: str
    trend_score: float
    image_url: Optional[str]
    status: str
    notes: Optional[str]


def init_db(path: Path = DB_PATH) -> None:
    LOGGER.info("Initializing database at %s", path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                first_seen TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                trend_score REAL NOT NULL DEFAULT 0,
                image_url TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                reviews INTEGER,
                orders INTEGER,
                price REAL,
                currency TEXT,
                social_mentions INTEGER,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL,
                found_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_platform ON sources(platform)")
    LOGGER.info("Database initialized")


@contextmanager
def get_conn(path: Path = DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def upsert_product(record: ProductRecord, *, conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "SELECT id, trend_score, status FROM products WHERE name = ?",
        (record.name,),
    )
    row = cursor.fetchone()
    now = datetime.utcnow().isoformat()
    if row:
        product_id = row["id"]
        trend_score = compute_trend_score(record, existing_score=row["trend_score"])
        conn.execute(
            """
            UPDATE products
            SET last_updated = ?, trend_score = ?, image_url = COALESCE(?, image_url)
            WHERE id = ?
            """,
            (now, trend_score, record.image_url, product_id),
        )
    else:
        trend_score = compute_trend_score(record)
        cursor = conn.execute(
            """
            INSERT INTO products (name, category, first_seen, last_updated, trend_score, image_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.name,
                record.metadata.get("category") if record.metadata else None,
                now,
                now,
                trend_score,
                record.image_url,
                "new",
            ),
        )
        product_id = cursor.lastrowid
    LOGGER.debug("Upserted product %s -> id %s", record.name, product_id)
    return product_id


def add_metric(product_id: int, record: ProductRecord, *, conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO metrics (product_id, date, reviews, orders, price, currency, social_mentions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            datetime.utcnow().date().isoformat(),
            record.reviews,
            record.orders,
            record.price,
            record.currency,
            record.metadata.get("social_mentions") if record.metadata else None,
        ),
    )


def add_source(product_id: int, record: ProductRecord, *, conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO sources (product_id, platform, url, found_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            product_id,
            record.platform,
            record.url,
            datetime.utcnow().isoformat(),
        ),
    )


def persist_records(records: Iterable[ProductRecord], path: Path = DB_PATH) -> None:
    if not records:
        return
    with get_conn(path) as conn:
        for record in records:
            product_id = upsert_product(record, conn=conn)
            add_metric(product_id, record, conn=conn)
            add_source(product_id, record, conn=conn)
        conn.commit()


def compute_trend_score(record: ProductRecord, existing_score: float | None = None) -> float:
    base_score = existing_score or 0
    score = base_score * 0.7
    reviews = record.reviews or 0
    orders = record.orders or 0
    badges = len(record.badges or [])
    rating = record.rating or 0

    score += min(reviews / 100, 40)
    score += min(orders / 50, 30)
    score += badges * 5
    score += (rating / 5) * 10
    if record.metadata:
        if record.metadata.get("source_url", "").startswith("https://www.reddit.com"):
            score += 5
    return round(min(score, 100), 2)


def update_status(product_id: int, status: str, notes: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
            (status, notes, product_id),
        )
        conn.commit()

