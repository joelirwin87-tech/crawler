"""Scraper for Reddit rising posts."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, List

from bs4 import BeautifulSoup
from selenium.webdriver import Chrome

from config import SELECTORS
from .base_scraper import ProductRecord, SeleniumScraper, safe_int

LOGGER = logging.getLogger(__name__)


class RedditRisingScraper(SeleniumScraper):
    platform = "reddit"

    def __init__(self, subreddits: Iterable[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.subreddits = tuple(subreddits or (
            "shutupandtakemymoney",
            "ineeeedit",
        ))
        self.start_urls = tuple(
            f"https://www.reddit.com/r/{subreddit}/rising/" for subreddit in self.subreddits
        )

    def parse(self, driver: Chrome, url: str) -> List[ProductRecord]:
        selector = SELECTORS[self.platform]
        self.wait_for_any(driver, [selector.product_container])
        soup = BeautifulSoup(driver.page_source, "html.parser")
        records: List[ProductRecord] = []
        for post in soup.select(selector.product_container):
            title_el = post.select_one(selector.name)
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link_el = post.select_one(selector.link)
            post_url = (
                f"https://www.reddit.com{link_el['href']}" if link_el and link_el.has_attr("href")
                else url
            )
            subreddit_el = post.select_one(selector.badges.get("subreddit", "")) if selector.badges else None
            subreddit = subreddit_el.get_text(strip=True) if subreddit_el else None
            upvote_el = post.select_one("div[data-click-id='upvote'] span")
            upvotes = safe_int(upvote_el.get_text() if upvote_el else None)
            age_el = post.select_one("a[data-click-id='timestamp']")
            age = age_el.get_text(strip=True) if age_el else None

            metadata = {
                "source_url": driver.current_url,
                "subreddit": subreddit,
                "age": age,
                "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
            }

            record = ProductRecord(
                name=title,
                url=post_url,
                platform=self.platform,
                badges=[subreddit] if subreddit else None,
                reviews=upvotes,
                metadata=metadata,
            )
            if upvotes and upvotes < 100:
                continue
            records.append(record)
        LOGGER.info("Parsed %d posts from Reddit page", len(records))
        return records

