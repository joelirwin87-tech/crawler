"""Scraper for AliExpress hot and new products."""
from __future__ import annotations

import logging
from typing import List

from bs4 import BeautifulSoup
from selenium.webdriver import Chrome

from config import SELECTORS
from .base_scraper import ProductRecord, SeleniumScraper, parse_price, safe_int

LOGGER = logging.getLogger(__name__)


class AliExpressTrendingScraper(SeleniumScraper):
    platform = "aliexpress"
    start_urls = (
        "https://www.aliexpress.com/category/200003482/new-arrivals.html",
        "https://www.aliexpress.com/category/200003482/hot-products.html",
    )

    def parse(self, driver: Chrome, url: str) -> List[ProductRecord]:
        selector = SELECTORS[self.platform]
        self.wait_for_any(driver, [selector.product_container])
        soup = BeautifulSoup(driver.page_source, "html.parser")
        records: List[ProductRecord] = []
        badge_selector = ",".join(filter(None, selector.badges.values())) if selector.badges else ""
        for product in soup.select(selector.product_container):
            name_el = product.select_one(selector.name)
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            link_el = product.select_one(selector.link)
            product_url = link_el.get("href") if link_el else url
            price_el = product.select_one(selector.price) if selector.price else None
            price, currency = parse_price(price_el.get_text() if price_el else None)
            image_el = product.select_one(selector.image) if selector.image else None
            image = image_el.get("src") if image_el else None
            orders_el = product.select_one(selector.orders) if selector.orders else None
            orders = safe_int(orders_el.get_text() if orders_el else None)
            badges = [badge.get_text(strip=True) for badge in product.select(badge_selector)] if badge_selector else []

            metadata = {
                "source_url": driver.current_url,
            }

            record = ProductRecord(
                name=name,
                url=product_url,
                platform=self.platform,
                price=price,
                currency=currency,
                image_url=image,
                orders=orders,
                badges=badges,
                metadata=metadata,
            )
            if self._passes_filters(record):
                records.append(record)
        LOGGER.info("Parsed %d products from AliExpress page", len(records))
        return records

    def _passes_filters(self, record: ProductRecord) -> bool:
        if record.orders and record.orders > 1000:
            return False
        return True

