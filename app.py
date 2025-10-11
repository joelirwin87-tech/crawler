"""Streamlit dashboard for the lightweight trending product bot."""
from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Dict, Iterable, List

import streamlit as st

from database import fetch_metrics_for_product, fetch_products, init_db
from run_scrapers import run_all


def main() -> None:
    st.set_page_config(page_title="Trending Product Radar", layout="wide")
    st.title("Trending Product Radar")
    init_db()

    if "last_run" not in st.session_state:
        st.session_state["last_run"] = None

    products = _load_products()

    with st.sidebar:
        st.header("Controls")
        if st.button("Run Scrapers"):
            with st.spinner("Running scrapers..."):
                results = run_all()
                st.session_state["last_run"] = datetime.utcnow().isoformat()
                st.success(f"Captured {len(results)} results")
                products = _load_products()
        st.header("Filters")
        platform_options = sorted({item["platform"] for item in products if item.get("platform")})
        min_score = st.slider("Minimum Trend Score", 0, 100, value=40)
        selected_platforms = st.multiselect("Platforms", options=platform_options)

        use_start = st.checkbox("Filter by first seen date")
        start_date = st.date_input(
            "First Seen On/After",
            value=date.today(),
            disabled=not use_start,
        )
        if not use_start:
            start_date = None

        use_end = st.checkbox("Filter by last seen date")
        end_date = st.date_input(
            "Last Seen On/Before",
            value=date.today(),
            disabled=not use_end,
        )
        if not use_end:
            end_date = None

    filtered = _filter_products(products, selected_platforms, min_score, start_date, end_date)

    st.subheader("Trending Products")
    if not filtered:
        st.info("No products available yet. Run the scrapers to gather data.")
    else:
        st.dataframe(
            [
                {
                    "Name": item["name"],
                    "Platform": item["platform"],
                    "Trend Score": item["trend_score"],
                    "Reviews": item.get("reviews"),
                    "Orders": item.get("orders"),
                    "Votes": item.get("votes"),
                    "First Seen": item.get("first_seen"),
                    "Last Seen": item.get("last_seen"),
                }
                for item in filtered
            ],
            use_container_width=True,
        )
        st.download_button(
            "Download Filtered CSV",
            data=_build_csv(filtered),
            file_name="trending_products_filtered.csv",
            mime="text/csv",
        )

        st.subheader("Product Highlights")
        for product in filtered:
            _render_product_card(product)

    if st.session_state["last_run"]:
        st.caption(f"Last scraper run: {st.session_state['last_run']}")


def _load_products() -> List[Dict[str, object]]:
    rows = fetch_products()
    return [dict(row) for row in rows]


def _filter_products(
    products: Iterable[Dict[str, object]],
    platforms: List[str],
    min_score: int,
    start: date | None,
    end: date | None,
) -> List[Dict[str, object]]:
    filtered: List[Dict[str, object]] = []
    for product in products:
        if platforms and product.get("platform") not in platforms:
            continue
        if product.get("trend_score", 0) < min_score:
            continue
        first_seen = _to_date(product.get("first_seen"))
        last_seen = _to_date(product.get("last_seen"))
        if start and first_seen and first_seen < start:
            continue
        if end and last_seen and last_seen > end:
            continue
        filtered.append(product)
    return filtered


def _render_product_card(product: Dict[str, object]) -> None:
    st.markdown("---")
    left, right = st.columns([1, 3])
    if product.get("image_url"):
        left.image(product["image_url"], use_column_width=True)
    left.metric("Trend Score", f"{product.get('trend_score', 0):.1f}")

    right.markdown(f"### {product['name']}")
    right.markdown(f"**Platform:** {product['platform']}")
    if product.get("url"):
        right.markdown(f"[Open listing]({product['url']})")

    metrics_summary = []
    reviews = _safe_int(product.get("reviews"))
    if reviews:
        metrics_summary.append(f"{reviews} reviews")
    orders = _safe_int(product.get("orders"))
    if orders:
        metrics_summary.append(f"{orders} orders")
    votes = _safe_int(product.get("votes"))
    if votes:
        metrics_summary.append(f"{votes} votes")
    if metrics_summary:
        right.markdown(" | ".join(metrics_summary))

    history = fetch_metrics_for_product(product["id"], limit=25)
    if history:
        chart_data = {
            "Reviews": [row["reviews"] or 0 for row in history],
            "Orders": [row["orders"] or 0 for row in history],
            "Votes": [row["votes"] or 0 for row in history],
        }
        if any(sum(series) for series in chart_data.values()):
            right.line_chart(chart_data)


def _build_csv(products: Iterable[Dict[str, object]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "name",
            "platform",
            "url",
            "trend_score",
            "reviews",
            "orders",
            "votes",
            "first_seen",
            "last_seen",
        ]
    )
    for item in products:
        writer.writerow(
            [
                item.get("id"),
                item.get("name"),
                item.get("platform"),
                item.get("url"),
                item.get("trend_score"),
                item.get("reviews"),
                item.get("orders"),
                item.get("votes"),
                item.get("first_seen"),
                item.get("last_seen"),
            ]
        )
    return buffer.getvalue()


def _safe_int(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _to_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


if __name__ == "__main__":
    main()
