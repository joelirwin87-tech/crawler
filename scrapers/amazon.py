"""Selenium scraper for Amazon Movers & Shakers."""
from __future__ import annotations

import logging
from typing import Dict, List

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException

from config import AMAZON_MOVERS_URL, MAX_PRODUCTS_PER_SOURCE
from scrapers import selenium_session, sleep_random, wait_for_any

logger = logging.getLogger(__name__)


def scrape() -> List[Dict[str, object]]:
    """Return trending product payloads from Amazon."""
    results: List[Dict[str, object]] = []
    with selenium_session() as driver:
        logger.info("Loading Amazon movers page: %s", AMAZON_MOVERS_URL)
        try:
            driver.get(AMAZON_MOVERS_URL)
            wait_for_any(
                driver,
                [
                    ("CSS_SELECTOR", "div.p13n-gridRow"),
                    ("CSS_SELECTOR", "div#gridItemRoot"),
                ],
                timeout=30,
            )
        except TimeoutException:
            logger.warning("Timed out waiting for Amazon content")
            return results

        sleep_random()
        page_source = driver.page_source
        if "captcha" in page_source.lower() or "robot check" in page_source.lower():
            logger.warning("Amazon presented a CAPTCHA challenge; skipping run")
            return results

        soup = BeautifulSoup(page_source, "html.parser")
        product_nodes = soup.select("div.p13n-gridRow div.zg-grid-general-faceout, div#gridItemRoot")

        for node in product_nodes[:MAX_PRODUCTS_PER_SOURCE]:
            info = _parse_product(node)
            if not info:
                continue
            info["platform"] = "Amazon"
            info["metrics"] = _build_metrics(info)
            results.append(info)
            sleep_random()

    return results


def _parse_product(node) -> Dict[str, object] | None:
    title_elem = node.select_one("span._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, span.p13n-sc-truncate")
    link_elem = node.select_one("a.a-link-normal")
    if not title_elem or not link_elem:
        return None

    name = title_elem.get_text(strip=True)
    url = link_elem.get("href")
    if url and url.startswith("/"):
        url = f"https://www.amazon.com{url}"

    image_elem = node.select_one("img")
    rating_elem = node.select_one("span.a-icon-alt")
    reviews_elem = node.select_one("span.a-size-small.a-color-secondary")
    price_elem = node.select_one("span.p13n-sc-price")

    payload: Dict[str, object] = {
        "name": name,
        "url": url,
        "image_url": image_elem.get("src") if image_elem else None,
    }

    if rating_elem:
        rating_text = rating_elem.get_text(strip=True).split(" ")[0]
        try:
            payload["rating"] = float(rating_text)
        except ValueError:
            pass
    if reviews_elem:
        try:
            payload["reviews"] = int(reviews_elem.get_text(strip=True).replace(",", ""))
        except ValueError:
            pass
    if price_elem:
        price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "")
        try:
            payload["price"] = float(price_text)
        except ValueError:
            pass

    return payload


def _build_metrics(info: Dict[str, object]) -> Dict[str, object]:
    metrics: Dict[str, object] = {
        "reviews": info.get("reviews"),
        "rating": info.get("rating"),
        "price": info.get("price"),
    }
    if info.get("reviews") is not None:
        metrics["votes"] = info["reviews"]
    return metrics
