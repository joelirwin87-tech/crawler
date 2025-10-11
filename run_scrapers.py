"""Manual entry point to run all scrapers sequentially."""
from __future__ import annotations

import argparse
import logging
import time
from typing import Dict, List

import schedule

from database import init_db, record_products
from scrapers import sleep_random
from scrapers import aliexpress, amazon, reddit

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def run_all() -> List[Dict[str, object]]:
    """Run all available scrapers and persist their findings."""
    init_db()
    harvested: List[Dict[str, object]] = []

    for name, scraper in (
        ("amazon", amazon.scrape),
        ("aliexpress", aliexpress.scrape),
        ("reddit", reddit.scrape),
    ):
        try:
            logger.info("Starting %s scraper", name)
            results = scraper()
            for payload in results:
                payload["trend_score"] = _compute_trend_score(payload)
                payload.setdefault("description", f"Discovered via {payload['platform']}")
            harvested.extend(results)
            sleep_random()
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s scraper failed: %s", name, exc)

    if harvested:
        logger.info("Persisting %s product records", len(harvested))
        record_products(harvested)
    else:
        logger.info("No new records harvested")

    return harvested


def run_scheduler(interval_hours: float) -> None:
    """Continuously run the scrapers on a simple interval."""
    logger.info("Scheduling scrapes every %.2f hours", interval_hours)
    schedule.clear()
    schedule.every(interval_hours).hours.do(run_all)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


def _compute_trend_score(payload: Dict[str, object]) -> float:
    metrics = payload.get("metrics", {})
    rating = metrics.get("rating") or payload.get("rating") or 0
    reviews = metrics.get("reviews") or payload.get("reviews") or 0
    orders = metrics.get("orders") or payload.get("orders") or 0
    votes = metrics.get("votes") or payload.get("votes") or 0
    comments = metrics.get("comments") or payload.get("comments") or 0

    if isinstance(reviews, str):
        reviews = _safe_int(reviews)
    if isinstance(orders, str):
        orders = _safe_int(orders)
    if isinstance(votes, str):
        votes = _safe_int(votes)
    if isinstance(comments, str):
        comments = _safe_int(comments)

    score = 10.0
    if rating:
        if rating >= 4.7:
            score += 25
        elif rating >= 4.3:
            score += 15
        elif rating >= 4.0:
            score += 8
    if reviews:
        if reviews < 500:
            score += 20
        elif reviews < 2000:
            score += 10
        elif reviews > 10000:
            score -= 15
    if orders:
        if 100 <= orders <= 2000:
            score += 20
        elif orders < 100:
            score += 10
        elif orders > 4000:
            score -= 10
    if votes:
        if votes > 2000:
            score += 25
        elif votes > 500:
            score += 15
        elif votes > 100:
            score += 8
    if comments and comments > 100:
        score += 5

    return max(0.0, min(score, 100.0))


def _safe_int(value) -> int | None:
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run trending product scrapers")
    parser.add_argument(
        "--schedule",
        type=float,
        default=0.0,
        help="Run continuously every N hours (defaults to a single run)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.schedule and args.schedule > 0:
        run_scheduler(args.schedule)
    else:
        run_all()
