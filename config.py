"""Application configuration for the lightweight trending product bot."""
from __future__ import annotations

import os
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("TRENDING_PRODUCTS_DATA", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "trending_products.db"

HEADLESS = os.environ.get("TRENDING_PRODUCTS_HEADLESS", "true").lower() != "false"
PAGE_LOAD_TIMEOUT = int(os.environ.get("TRENDING_PRODUCTS_TIMEOUT", 45))
MIN_DELAY = float(os.environ.get("TRENDING_PRODUCTS_DELAY_MIN", 2))
MAX_DELAY = float(os.environ.get("TRENDING_PRODUCTS_DELAY_MAX", 5))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
]

AMAZON_MOVERS_URL = os.environ.get(
    "TRENDING_PRODUCTS_AMAZON_URL",
    "https://www.amazon.com/gp/movers-and-shakers/",
)
ALIEXPRESS_TRENDING_URL = os.environ.get(
    "TRENDING_PRODUCTS_ALIEXPRESS_URL",
    "https://www.aliexpress.com/category/100003109/women-clothing.html?trafficChannel=main&SortType=bestmatch_sort",
)
REDDIT_TRENDING_URL = os.environ.get(
    "TRENDING_PRODUCTS_REDDIT_URL",
    "https://www.reddit.com/r/shutupandtakemymoney/hot/",
)

MAX_PRODUCTS_PER_SOURCE = int(os.environ.get("TRENDING_PRODUCTS_MAX_ITEMS", 25))


def random_delay() -> float:
    """Return a randomized sleep duration within the configured bounds."""
    return random.uniform(MIN_DELAY, MAX_DELAY)
