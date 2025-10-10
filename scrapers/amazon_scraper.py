"""Scraper for Amazon Movers & Shakers pages."""
from __future__ import annotations

import logging
from typing import List

from bs4 import BeautifulSoup
from selenium.webdriver import Chrome

from config import SELECTORS
from .base_scraper import ProductRecord, SeleniumScraper, parse_price, safe_float, safe_int

LOGGER = logging.getLogger(__name__)


class AmazonMoversShakersScraper(SeleniumScraper):
    platform = "amazon"
    start_urls = (
        "https://www.amazon.com/gp/movers-and-shakers",
        "https://www.amazon.com/gp/new-releases",
    )

    def parse(self, driver: Chrome, url: str) -> List[ProductRecord]:  # noqa: D401
        """Return parsed product records for the provided Amazon page."""

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
            url = (
                f"https://www.amazon.com{link_el['href']}" if link_el and link_el.has_attr("href")
                else driver.current_url
            )
            price_el = product.select_one(selector.price) if selector.price else None
            price, currency = parse_price(price_el.get_text() if price_el else None)
            rating_el = product.select_one(selector.rating) if selector.rating else None
            rating = safe_float(rating_el.get_text().split()[0] if rating_el else None)
            reviews_el = product.select_one(selector.reviews) if selector.reviews else None
            reviews = safe_int(reviews_el.get_text() if reviews_el else None)
            image_el = product.select_one(selector.image) if selector.image else None
            image = image_el.get("src") if image_el else None

            badges = [
                badge_el.get_text(strip=True)
                for badge_el in product.select(badge_selector)
            ] if badge_selector else []

            metadata = {
                "source_url": driver.current_url,
            }

            record = ProductRecord(
                name=name,
                url=url,
                platform=self.platform,
                price=price,
                currency=currency,
                image_url=image,
                reviews=reviews,
                rating=rating,
                badges=badges,
                metadata=metadata,
            )
            if self._passes_filters(record):
                records.append(record)
        LOGGER.info("Parsed %d products from Amazon page", len(records))
        return records

    def _passes_filters(self, record: ProductRecord) -> bool:
        """Amazon-specific anti-saturation filters."""

        if record.reviews and record.reviews > 10000:
            LOGGER.debug("Filtered %s due to high review count", record.name)
            return False
        if record.rating and record.rating < 4.0:
            return False
        return True

