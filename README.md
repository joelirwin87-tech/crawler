# Trending Product Radar (Lightweight Edition)

This project tracks early-stage trending products using Selenium-powered scrapers and a Streamlit dashboard. It focuses on three reliable, scrape-friendly sources—Amazon Movers & Shakers, AliExpress trending listings, and Reddit's r/shutupandtakemymoney—and stores results in a compact SQLite database.

The implementation prioritises macOS compatibility and minimal dependencies: only Selenium, undetected-chromedriver, BeautifulSoup, Requests, Streamlit, and Schedule are required.

## Features

- **Selenium scrapers** for Amazon, AliExpress, and Reddit with randomised delays, rotating user agents, and headless support.
- **Lightweight SQLite persistence** using Python's built-in `sqlite3` module (no ORMs or external DB drivers).
- **Simple trend scoring** based on reviews, orders, and engagement to highlight low-saturation opportunities.
- **Streamlit dashboard** offering filtering, sortable tables, quick product cards, and CSV export of the current view.
- **Manual or scheduled execution** via a helper script that uses the `schedule` library or cron/launchd on macOS.

## Project Structure

```
/crawler
├── app.py               # Streamlit dashboard
├── config.py            # Scraper configuration and settings
├── database.py          # SQLite helpers
├── run_scrapers.py      # Manual/scheduled scraper runner
├── requirements.txt     # Minimal dependency set
├── scrapers/
│   ├── __init__.py      # Selenium session utilities
│   ├── aliexpress.py    # AliExpress trending scraper
│   ├── amazon.py        # Amazon Movers & Shakers scraper
│   └── reddit.py        # Reddit product discussion scraper
└── README.md
```

## Prerequisites

- Python 3.12+
- Google Chrome or Chromium installed locally (Selenium requirement)
- macOS, Linux, or Windows host with the ability to run Chrome in headless mode

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running Scrapers

Perform a single scrape across all sources:

```bash
python run_scrapers.py
```

To keep scraping on a simple interval using the bundled scheduler:

```bash
python run_scrapers.py --schedule 12  # runs every 12 hours
```

For production automation on macOS, use `cron` or `launchd` to execute `python run_scrapers.py` at your preferred cadence.

## Launching the Dashboard

```bash
streamlit run app.py
```

Dashboard highlights:

- Sidebar controls to trigger scrapes, filter by platform, minimum trend score, or date range
- Ranked table of products with current review/order/vote counts
- Product cards with quick metrics and simple Streamlit charts
- One-click CSV export of the filtered dataset

## Configuration

The defaults in `config.py` can be overridden with environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `TRENDING_PRODUCTS_DATA` | Output directory for SQLite database | `./data` |
| `TRENDING_PRODUCTS_HEADLESS` | Set to `false` to show the browser | `true` |
| `TRENDING_PRODUCTS_TIMEOUT` | Page load timeout in seconds | `45` |
| `TRENDING_PRODUCTS_DELAY_MIN` | Minimum random delay between actions | `2` |
| `TRENDING_PRODUCTS_DELAY_MAX` | Maximum random delay between actions | `5` |
| `TRENDING_PRODUCTS_MAX_ITEMS` | Max products captured per source | `25` |
| `TRENDING_PRODUCTS_AMAZON_URL` | Override Amazon movers URL | official movers page |
| `TRENDING_PRODUCTS_ALIEXPRESS_URL` | Override AliExpress list URL | womens clothing trending |
| `TRENDING_PRODUCTS_REDDIT_URL` | Override Reddit feed URL | `/r/shutupandtakemymoney/hot/` |

## Extending Scrapers

1. Copy an existing scraper in `scrapers/` and adjust selectors for the new source.
2. Return dictionaries containing at least `name`, `url`, `platform`, and a `metrics` mapping (`reviews`, `orders`, `votes`, etc.).
3. Register the scraper in `run_scrapers.py` alongside the others.

## Troubleshooting

- **Chromedriver mismatches**: Ensure Chrome/Chromium is installed. `undetected-chromedriver` manages the driver binary automatically.
- **CAPTCHA or blocked pages**: The scrapers log failures and skip the entry. Consider adding proxy rotation if needed.
- **Empty dashboard**: Run `python run_scrapers.py` or use the Streamlit sidebar button to populate data.

Always respect each website's terms of service and scraping policies.
