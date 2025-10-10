# Trending Products Bot

A modular Selenium-based scraping system and Streamlit dashboard that tracks trending e-commerce products before they become saturated. The bot focuses on platforms such as Amazon Movers & Shakers, AliExpress New Arrivals, and Reddit rising posts, and can be extended to additional sources.

## Features

- **Selenium Scrapers** using `undetected-chromedriver` with random delays, user-agent rotation, optional proxies, and debugging artefacts (screenshots + HTML).
- **Anti-saturation heuristics** including review/order thresholds and rating filters.
- **SQLite persistence layer** with product, metric, and source tables.
- **APScheduler integration** for automated background scraping.
- **Streamlit dashboard** offering ranked tables, product cards, manual tagging, notes, Plotly trend charts, and log downloads.
- **Extensible architecture** to add new scrapers and metrics.

## Project Structure

```
/trending-products-bot
├── app.py                   # Streamlit dashboard
├── config.py                # Global configuration and selectors
├── database.py              # SQLite schema and persistence helpers
├── scheduler.py             # APScheduler wrapper for scraping jobs
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py      # Shared Selenium logic
│   ├── amazon_scraper.py    # Amazon Movers & Shakers + New Releases
│   ├── aliexpress_scraper.py# AliExpress hot/new arrivals
│   └── reddit_scraper.py    # Reddit rising posts
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Python 3.11+
- Google Chrome/Chromium installed on the host (required by Selenium)
- Optional: Docker & Docker Compose

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Scrapers Once

```bash
python -m scheduler
```

The command initialises the database (if necessary), runs each scraper sequentially, and persists results to `data/trending_products.sqlite3`.

## Streamlit Dashboard

```bash
streamlit run app.py
```

Dashboard capabilities include:

- Ranked list sorted by trend score
- Product cards with gauges, platform badges, Plotly charts, notes & status management
- Manual scraper trigger and log viewer
- History tab filtering for "pass"/"saturated" products

## Scheduler as a Service

To run scrapers on a schedule, use the helper functions in `scheduler.py` from a Python entrypoint:

```python
from scheduler import start_scheduler

if __name__ == "__main__":
    scheduler = start_scheduler()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()
```

Each scraper runs at an interval defined in `config.SCRAPE_INTERVAL_HOURS`. Intervals can be customised via environment variables such as `SCRAPE_INTERVAL_AMAZON`.

## Environment Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `TRENDING_PRODUCTS_DATA` | Output directory for DB and artefacts | `./data` |
| `TRENDING_PRODUCTS_HEADLESS` | Set to `false` to disable headless mode | `true` |
| `TRENDING_PRODUCTS_PROXY` | Proxy URL passed to Chrome | unset |
| `TRENDING_PRODUCTS_DELAY_MIN` | Minimum random delay seconds | `2` |
| `TRENDING_PRODUCTS_DELAY_MAX` | Maximum random delay seconds | `5` |
| `SCRAPE_INTERVAL_AMAZON` | Hours between Amazon runs | `12` |
| `SCRAPE_INTERVAL_ALIEXPRESS` | Hours between AliExpress runs | `12` |
| `SCRAPE_INTERVAL_REDDIT` | Hours between Reddit runs | `24` |

## Docker Usage

Build and run using Docker Compose for reproducible deployments:

```bash
docker compose up --build
```

The `web` service serves the Streamlit dashboard on port 8501, while the `scheduler` service runs periodic scrapes.

## Extending with New Scrapers

1. Create a new module in `scrapers/` inheriting from `SeleniumScraper`.
2. Add CSS selectors to `config.SELECTORS`.
3. Implement a `parse` method returning `ProductRecord` instances.
4. Register the scraper in `scheduler.SCRAPERS` and `config.SCRAPE_INTERVAL_HOURS`.

## Troubleshooting

- **Chromedriver issues**: Ensure Chrome/Chromium is installed and matches the major version expected by `undetected-chromedriver`.
- **CAPTCHA detection**: The scraper logs skipped pages; manual intervention may be required for persistent CAPTCHAs.
- **Empty datasets**: Use the Streamlit sidebar button to trigger scrapes manually.

## License

This project is provided as-is for educational purposes. Ensure compliance with the Terms of Service of any website you scrape and respect `robots.txt` directives.

