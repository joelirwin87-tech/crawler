"""Selenium scraper for Reddit trending posts."""
from __future__ import annotations

import logging
from typing import Dict, List

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException

from config import MAX_PRODUCTS_PER_SOURCE, REDDIT_TRENDING_URL
from scrapers import selenium_session, sleep_random, wait_for_any

logger = logging.getLogger(__name__)


def scrape() -> List[Dict[str, object]]:
    """Return product-like payloads derived from Reddit posts."""
    results: List[Dict[str, object]] = []
    with selenium_session() as driver:
        logger.info("Loading Reddit feed: %s", REDDIT_TRENDING_URL)
        try:
            driver.get(REDDIT_TRENDING_URL)
            wait_for_any(
                driver,
                [
                    ("CSS_SELECTOR", "div[data-testid='post-container']"),
                    ("CSS_SELECTOR", "div.Post"),
                ],
                timeout=30,
            )
        except TimeoutException:
            logger.warning("Timed out waiting for Reddit content")
            return results

        sleep_random()
        page_source = driver.page_source
        if "captcha" in page_source.lower():
            logger.warning("Reddit presented a CAPTCHA challenge; skipping run")
            return results

        soup = BeautifulSoup(page_source, "html.parser")
        post_nodes = soup.select("div[data-testid='post-container'], div.Post")

        for node in post_nodes[:MAX_PRODUCTS_PER_SOURCE]:
            info = _parse_post(node)
            if not info:
                continue
            info["platform"] = "Reddit"
            info["metrics"] = {
                "votes": info.get("votes"),
                "comments": info.get("comments"),
            }
            results.append(info)
            sleep_random()

    return results


def _parse_post(node) -> Dict[str, object] | None:
    title_elem = node.select_one("h3")
    link_elem = node.select_one("a[data-click-id='body'], a[data-testid='post-container']")
    if not title_elem or not link_elem:
        return None

    name = title_elem.get_text(strip=True)
    url = link_elem.get("href")
    if url and url.startswith("/"):
        url = f"https://www.reddit.com{url}"

    votes_elem = node.select_one(
        "div[data-testid='upvoteRatio'], div[data-click-id='upvote'] span, div._1rZYMD_4xY3gRcSS3p8ODO"
    )
    comments_elem = node.select_one(
        "span[data-testid='comments-page-link-num-comments'], span.FHCV02u6Cp2zYL0fhQPsO"
    )
    timestamp_elem = node.select_one("a[data-click-id='timestamp']")

    payload: Dict[str, object] = {
        "name": name,
        "url": url,
    }

    if votes_elem:
        payload["votes"] = _parse_count(votes_elem.get_text(strip=True))
    if comments_elem:
        payload["comments"] = _parse_count(comments_elem.get_text(strip=True).split(" ")[0])
    if timestamp_elem and payload.get("votes") is not None:
        payload["description"] = f"Reddit post captured at {timestamp_elem.get_text(strip=True)}"

    return payload


def _parse_count(text: str) -> int | None:
    text = text.lower().replace("points", "").replace("point", "").strip()
    if not text:
        return None
    multiplier = 1
    if text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None
