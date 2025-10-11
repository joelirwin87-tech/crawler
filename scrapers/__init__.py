"""Utilities shared by the Selenium scrapers."""
from __future__ import annotations

import contextlib
import logging
import random
import time
from typing import Iterator

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import HEADLESS, PAGE_LOAD_TIMEOUT, USER_AGENTS, random_delay

LOGGER = logging.getLogger(__name__)


@contextlib.contextmanager
def selenium_session(*, headless: bool | None = None) -> Iterator[uc.Chrome]:
    """Yield an undetected Chrome session with randomized user agent."""
    options = Options()
    options.headless = HEADLESS if headless is None else headless
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,900")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    try:
        yield driver
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


def wait_for_any(driver, selectors: list[tuple[str, str]], timeout: int = 20) -> None:
    """Wait until one of the CSS selectors is present on the page."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        for by, value in selectors:
            by_member = getattr(By, by.upper(), None)
            if not by_member:
                LOGGER.debug("Unsupported locator strategy: %s", by)
                continue
            try:
                WebDriverWait(driver, 1).until(EC.presence_of_element_located((by_member, value)))
                return
            except Exception:
                continue
        time.sleep(0.5)
    raise TimeoutError(f"No selector found within {timeout} seconds: {selectors}")


def sleep_random() -> None:
    time.sleep(random_delay())
