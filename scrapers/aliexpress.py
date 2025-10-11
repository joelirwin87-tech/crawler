"""Selenium scraper for AliExpress trending listings."""
from __future__ import annotations

import logging
from typing import Dict, List

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException

from config import ALIEXPRESS_TRENDING_URL, MAX_PRODUCTS_PER_SOURCE
from scrapers import selenium_session, sleep_random, wait_for_any

logger = logging.getLogger(__name__)


def scrape() -> List[Dict[str, object]]:
    """Return trending product payloads from AliExpress."""
    results: List[Dict[str, object]] = []
    with selenium_session() as driver:
        logger.info("Loading AliExpress trending page: %s", ALIEXPRESS_TRENDING_URL)
        try:
            driver.get(ALIEXPRESS_TRENDING_URL)
            wait_for_any(
                driver,
                [
                    ("CSS_SELECTOR", "div.JIIxO"),
                    ("CSS_SELECTOR", "div.list-item"),
                ],
                timeout=30,
            )
        except TimeoutException:
            logger.warning("Timed out waiting for AliExpress content")
            return results

        sleep_random()
        page_source = driver.page_source
        if "captcha" in page_source.lower():
            logger.warning("AliExpress presented a CAPTCHA challenge; skipping run")
            return results

        soup = BeautifulSoup(page_source, "html.parser")
        product_nodes = soup.select("div.JIIxO, div.list-item")

        for node in product_nodes[:MAX_PRODUCTS_PER_SOURCE]:
            info = _parse_product(node)
            if not info:
                continue
            info["platform"] = "AliExpress"
            info["metrics"] = _build_metrics(info)
            results.append(info)
            sleep_random()

    return results


def _parse_product(node) -> Dict[str, object] | None:
    title_elem = node.select_one("a._3t7zg, a.item-title")
    if not title_elem:
        return None

    name = title_elem.get_text(strip=True)
    url = title_elem.get("href")
    if url and url.startswith("//"):
        url = f"https:{url}"

    image_elem = node.select_one("img")
    price_elem = node.select_one("div._1NoI8, span.price")
    orders_elem = node.select_one("span._1kNf9, span.item-sold")
    rating_elem = node.select_one("span._1cE1T")

    payload: Dict[str, object] = {
        "name": name,
        "url": url,
        "image_url": image_elem.get("src") if image_elem else None,
    }

    if price_elem:
        price_text = (
            price_elem.get_text(strip=True)
            .replace("US $", "")
            .replace("$", "")
            .replace(",", "")
        )
        try:
            payload["price"] = float(price_text)
        except ValueError:
            pass
    if orders_elem:
        orders_text = orders_elem.get_text(strip=True).split(" ")[0].replace(",", "")
        try:
            payload["orders"] = int(orders_text)
        except ValueError:
            pass
    if rating_elem:
        try:
            payload["rating"] = float(rating_elem.get_text(strip=True))
        except ValueError:
            pass

    return payload


def _build_metrics(info: Dict[str, object]) -> Dict[str, object]:
    return {
        "orders": info.get("orders"),
        "price": info.get("price"),
        "rating": info.get("rating"),
    }
