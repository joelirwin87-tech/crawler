"""Background scheduler for the trending products bot."""
from __future__ import annotations

import logging
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, Iterable, Type

from apscheduler.schedulers.background import BackgroundScheduler

from config import DATA_DIR, SCRAPE_INTERVAL_HOURS
from database import init_db, persist_records
from scrapers import (
    AliExpressTrendingScraper,
    AmazonMoversShakersScraper,
    RedditRisingScraper,
)
from scrapers.base_scraper import SeleniumScraper

LOGGER = logging.getLogger(__name__)

SCRAPERS: Dict[str, Type[SeleniumScraper]] = {
    "amazon": AmazonMoversShakersScraper,
    "aliexpress": AliExpressTrendingScraper,
    "reddit": RedditRisingScraper,
}


class ScraperScheduler:
    """Wrapper around APScheduler that sequentially runs scrapers."""

    def __init__(self, scraper_names: Iterable[str] | None = None):
        self.scheduler = BackgroundScheduler()
        self.scraper_names = tuple(scraper_names or SCRAPERS.keys())

    def start(self) -> None:
        init_db()
        for name in self.scraper_names:
            scraper_cls = SCRAPERS[name]
            interval_hours = SCRAPE_INTERVAL_HOURS.get(name, 24)
            LOGGER.info("Scheduling %s every %s hours", name, interval_hours)
            self.scheduler.add_job(
                self._run_scraper,
                "interval",
                hours=interval_hours,
                args=[scraper_cls],
                id=name,
                replace_existing=True,
            )
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown()

    def run_now(self) -> None:
        for name in self.scraper_names:
            self._run_scraper(SCRAPERS[name])

    def _run_scraper(self, scraper_cls: Type[SeleniumScraper]) -> None:
        LOGGER.info("Running scraper %s", scraper_cls.__name__)
        scraper = scraper_cls()
        records = scraper.fetch()
        persist_records(records)
        LOGGER.info("Persisted %d records from %s", len(records), scraper_cls.__name__)


def run_once(scraper_names: Iterable[str] | None = None) -> None:
    init_db()
    names = tuple(scraper_names or SCRAPERS.keys())
    for name in names:
        scraper_cls = SCRAPERS[name]
        LOGGER.info("Running scraper %s", name)
        scraper = scraper_cls()
        persist_records(scraper.fetch())


def start_scheduler(scraper_names: Iterable[str] | None = None) -> ScraperScheduler:
    scheduler = ScraperScheduler(scraper_names=scraper_names)
    scheduler.start()
    return scheduler


def configure_logging() -> None:
    log_path = DATA_DIR / "scraper.log"
    handlers = [logging.StreamHandler(), logging.FileHandler(log_path, encoding="utf-8")]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
    )
    LOGGER.info("Logging configured -> %s", log_path)


def main() -> None:
    configure_logging()
    parser = ArgumentParser(description="Run trending product scrapers")
    parser.add_argument("--schedule", action="store_true", help="Start scheduler instead of one-off run")
    parser.add_argument("--scrapers", nargs="*", help="Subset of scrapers to run")
    args = parser.parse_args()

    targets = args.scrapers or None
    if args.schedule:
        scheduler = start_scheduler(scraper_names=targets)
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.shutdown()
    else:
        run_once(scraper_names=targets)


if __name__ == "__main__":
    main()

