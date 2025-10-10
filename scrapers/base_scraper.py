"""Shared Selenium scraping utilities."""
from __future__ import annotations

import json
import logging
import random
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import (
    DEFAULT_HEADLESS,
    HTML_DEBUG_DIR,
    PAGE_LOAD_TIMEOUT,
    PROXY_URL,
    RANDOM_DELAY_RANGE,
    SCREENSHOT_DIR,
    SELECTORS,
    USER_AGENTS,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ProductRecord:
    """Normalized product information returned by scrapers."""

    name: str
    url: str
    platform: str
    price: Optional[float] = None
    currency: Optional[str] = None
    image_url: Optional[str] = None
    reviews: Optional[int] = None
    rating: Optional[float] = None
    orders: Optional[int] = None
    badges: Optional[List[str]] = None
    metadata: Optional[dict] = None


class SeleniumScraper(ABC):
    """Base Selenium scraper that encapsulates defensive scraping behavior."""

    platform: str
    start_urls: Iterable[str]

    def __init__(self, headless: bool | None = None, *,
                 proxy: str | None = PROXY_URL, screenshot_dir: Path = SCREENSHOT_DIR):
        self.headless = DEFAULT_HEADLESS if headless is None else headless
        self.proxy = proxy
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.random = random.Random()
        self.random.seed()
        LOGGER.debug("Initialized scraper %s headless=%s proxy=%s", self.__class__.__name__, self.headless, proxy)

    @contextmanager
    def driver(self) -> Iterable[Chrome]:
        """Context manager that yields a configured undetected-chromedriver instance."""

        user_agent = self.random.choice(USER_AGENTS)
        options = Options()
        options.headless = self.headless
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-agent={user_agent}")
        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        LOGGER.debug("Launching Chrome with user-agent=%s", user_agent)
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

        try:
            yield driver
        finally:
            driver.quit()

    @abstractmethod
    def parse(self, driver: Chrome, url: str) -> List[ProductRecord]:
        """Parse a page and return normalized product records."""

    def fetch(self) -> List[ProductRecord]:
        """Iterate over configured URLs and collect product records."""

        records: List[ProductRecord] = []
        with self.driver() as driver:
            for url in self.start_urls:
                try:
                    LOGGER.info("Scraping %s", url)
                    driver.get(url)
                    self._random_delay()
                    records.extend(self.parse(driver, url))
                except TimeoutException:
                    LOGGER.warning("Timeout fetching %s", url, exc_info=True)
                except Exception:  # pylint: disable=broad-except
                    LOGGER.exception("Unexpected error scraping %s", url)
                    self._capture_debug_artifacts(driver, url)
        return records

    def wait_for_any(self, driver: Chrome, selectors: List[str], by: By = By.CSS_SELECTOR, timeout: int = 30) -> None:
        """Wait until any selector from the provided list is visible."""

        wait = WebDriverWait(driver, timeout)
        for selector in selectors:
            try:
                wait.until(EC.visibility_of_element_located((by, selector)))
                return
            except TimeoutException:
                LOGGER.debug("Timeout waiting for selector %s on %s", selector, driver.current_url)
        raise TimeoutException(f"None of the selectors appeared: {selectors}")

    def _capture_debug_artifacts(self, driver: Chrome, url: str) -> None:
        """Persist HTML and screenshot artefacts to help debugging failures."""

        timestamp = int(time.time())
        safe_name = url.replace("://", "_").replace("/", "_")[:100]
        screenshot_path = self.screenshot_dir / f"{safe_name}_{timestamp}.png"
        html_path = HTML_DEBUG_DIR / f"{safe_name}_{timestamp}.html"
        try:
            driver.save_screenshot(str(screenshot_path))
            LOGGER.info("Saved debug screenshot to %s", screenshot_path)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed saving screenshot")
        try:
            html = driver.page_source
            html_path.write_text(html, encoding="utf-8")
            LOGGER.info("Saved debug HTML to %s", html_path)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed saving HTML source")

    def _random_delay(self) -> None:
        delay = self.random.uniform(*RANDOM_DELAY_RANGE)
        LOGGER.debug("Sleeping for %.2f seconds", delay)
        time.sleep(delay)

    def selector(self, platform: str) -> Optional[dict]:
        return SELECTORS.get(platform)


def parse_price(raw_price: str | None) -> tuple[Optional[float], Optional[str]]:
    """Parse a price string into value and currency."""

    if not raw_price:
        return None, None
    cleaned = raw_price.strip()
    currency = cleaned[0] if cleaned and not cleaned[0].isdigit() else None
    digits = "".join(ch for ch in cleaned if ch.isdigit() or ch in ".,")
    digits = digits.replace(",", "")
    try:
        value = float(digits)
    except (TypeError, ValueError):
        return None, currency
    return value, currency


def safe_int(value: str | None) -> Optional[int]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    try:
        return int(digits)
    except ValueError:
        return None


def safe_float(value: str | None) -> Optional[float]:
    if not value:
        return None
    cleaned = value.split()[0]
    try:
        return float(cleaned)
    except ValueError:
        return None


def dump_records(records: List[ProductRecord], path: Path) -> None:
    """Persist a JSON snapshot of records for debugging."""

    payload = [record.__dict__ for record in records]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

