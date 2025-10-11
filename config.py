"""Central configuration for the trending products bot."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


DATA_DIR = Path(os.environ.get("TRENDING_PRODUCTS_DATA", Path.cwd() / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOT_DIR = DATA_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

HTML_DEBUG_DIR = DATA_DIR / "html"
HTML_DEBUG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HEADLESS = os.environ.get("TRENDING_PRODUCTS_HEADLESS", "true").lower() != "false"
PROXY_URL = os.environ.get("TRENDING_PRODUCTS_PROXY")
PAGE_LOAD_TIMEOUT = int(os.environ.get("TRENDING_PRODUCTS_TIMEOUT", 45))
IMPLICIT_WAIT = int(os.environ.get("TRENDING_PRODUCTS_IMPLICIT_WAIT", 5))
RANDOM_DELAY_RANGE = (float(os.environ.get("TRENDING_PRODUCTS_DELAY_MIN", 2)),
                      float(os.environ.get("TRENDING_PRODUCTS_DELAY_MAX", 5)))

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36",
]

SCRAPE_INTERVAL_HOURS = {
    "amazon": float(os.environ.get("SCRAPE_INTERVAL_AMAZON", 12)),
    "aliexpress": float(os.environ.get("SCRAPE_INTERVAL_ALIEXPRESS", 12)),
    "reddit": float(os.environ.get("SCRAPE_INTERVAL_REDDIT", 24)),
}


@dataclass(slots=True)
class SelectorConfig:
    """CSS/XPath selectors for scraper parsing."""

    product_container: str
    name: str
    price: str | None = None
    image: str | None = None
    link: str | None = None
    reviews: str | None = None
    rating: str | None = None
    orders: str | None = None
    badges: Dict[str, str] = field(default_factory=dict)


SELECTORS: Dict[str, SelectorConfig] = {
    "amazon": SelectorConfig(
        product_container="div.p13n-gridRow div.zg-grid-general-faceout",
        name="div.p13n-sc-truncate-desktop-type2, span._cDEzb_p13n-sc-css-line-clamp-3_g3dy1",
        price="span.p13n-sc-price, span._cDEzb_p13n-sc-price_3mJ9Z",
        image="img",
        link="a.a-link-normal",
        reviews="a.a-size-small.a-link-normal",
        rating="span.a-icon-alt",
        badges={"movers_shakers": "span.zg-bdg-text",
                "bestseller": "span._cDEzb_p13n-sc-badge-text_1v-nu"},
    ),
    "aliexpress": SelectorConfig(
        product_container="div.JIIxO",
        name="a._3t7zg",
        price="div._1NoI8",
        image="img",
        link="a._3t7zg",
        orders="span._1kNf9",
        badges={"hot": "span._1Kv4P"},
    ),
    "reddit": SelectorConfig(
        product_container="div.Post",
        name="h3",
        link="a[data-click-id='body']",
        badges={"subreddit": "a[data-click-id='subreddit']"},
    ),
}


LOG_LEVEL = os.environ.get("TRENDING_PRODUCTS_LOG_LEVEL", "INFO")

