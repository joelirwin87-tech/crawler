"""Streamlit dashboard for visualizing trending products."""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import DB_PATH, get_conn, init_db, update_status
from scheduler import run_once

logging.basicConfig(level=logging.INFO)

STATUS_OPTIONS = ["new", "researching", "ordered samples", "testing", "live", "pass", "saturated"]


@st.cache_data(show_spinner=False)
def load_products(start_date: Optional[date] = None, end_date: Optional[date] = None,
                 platforms: Optional[List[str]] = None,
                 min_score: float = 0.0) -> pd.DataFrame:
    with get_conn(DB_PATH) as conn:
        query = (
            """
            SELECT p.id, p.name, p.category, p.first_seen, p.last_updated, p.trend_score,
                   p.image_url, p.status, p.notes,
                   GROUP_CONCAT(DISTINCT s.platform) AS platforms,
                   GROUP_CONCAT(DISTINCT s.url) AS source_urls
            FROM products p
            LEFT JOIN sources s ON s.product_id = p.id
            GROUP BY p.id
            HAVING trend_score >= ?
            """
        )
        params: List[object] = [min_score]
        if platforms:
            query += " AND (" + " OR ".join("platforms LIKE ?" for _ in platforms) + ")"
            params.extend([f"%{platform}%" for platform in platforms])
        if start_date:
            query += " AND date(first_seen) >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND date(last_updated) <= ?"
            params.append(end_date.isoformat())
        df = pd.read_sql_query(query, conn, params=params)
    if not df.empty:
        df["platform_list"] = df["platforms"].fillna("").apply(lambda x: list(filter(None, x.split(","))))
    return df


def load_metrics(product_id: int) -> pd.DataFrame:
    with get_conn(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT date, reviews, orders, price FROM metrics WHERE product_id = ? ORDER BY date ASC",
            conn,
            params=[product_id],
        )
    return df


def render_gauge(score: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#FF4B4B"}},
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def render_product_card(row: pd.Series) -> None:
    st.markdown("---")
    cols = st.columns([1, 3])
    if row.image_url:
        cols[0].image(row.image_url, use_column_width=True)
    cols[1].markdown(f"### {row.name}")
    cols[1].plotly_chart(render_gauge(row.trend_score), use_container_width=True)
    platforms = row.get("platform_list", [])
    badge_text = " ".join(f"`{platform}`" for platform in platforms)
    cols[1].markdown(f"Platforms: {badge_text or 'N/A'}")
    if row.source_urls:
        for url in set(row.source_urls.split(",")):
            cols[1].markdown(f"[Source Link]({url})")
    with st.expander("Trend Metrics"):
        metrics_df = load_metrics(row.id)
        if metrics_df.empty:
            st.info("No metrics captured yet.")
        else:
            metrics_df["date"] = pd.to_datetime(metrics_df["date"])
            fig = px.line(metrics_df, x="date", y=["reviews", "orders", "price"], markers=True)
            st.plotly_chart(fig, use_container_width=True)
    with st.expander("Notes & Status"):
        default_index = STATUS_OPTIONS.index(row.status) if row.status in STATUS_OPTIONS else 0
        status = st.selectbox("Status", STATUS_OPTIONS, index=default_index, key=f"status_{row.id}")
        notes = st.text_area("Notes", value=row.notes or "", key=f"notes_{row.id}")
        if st.button("Save", key=f"save_{row.id}"):
            update_status(row.id, status, notes)
            st.success("Updated status")
            st.cache_data.clear()


def render_table(df: pd.DataFrame) -> None:
    table_df = df[["name", "trend_score", "category", "status", "first_seen", "last_updated", "platforms"]]
    st.dataframe(table_df.sort_values(by="trend_score", ascending=False), use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Trending Product Radar", layout="wide")
    st.title("Trending Product Radar")
    init_db()

    with st.sidebar:
        st.header("Scraper Controls")
        if st.button("Run Scrapers Now"):
            with st.spinner("Scraping..."):
                run_once()
                st.cache_data.clear()
                st.success("Scrape completed")
        st.write(f"Database: {DB_PATH}")

        st.header("Filters")
        min_score = st.slider("Minimum Trend Score", 0, 100, value=50)
        start_date = st.date_input("Start Date", value=None)
        end_date = st.date_input("End Date", value=None)
        selected_platforms = st.multiselect("Platforms", ["amazon", "aliexpress", "reddit"])

    df = load_products(start_date=start_date or None, end_date=end_date or None,
                       platforms=selected_platforms or None, min_score=float(min_score))

    st.subheader("Ranked Trending Products")
    if df.empty:
        st.info("No products available yet. Trigger a scrape to populate data.")
    else:
        render_table(df)
        st.subheader("Product Highlights")
        for _, row in df.iterrows():
            render_product_card(row)

    st.subheader("History & Exclusions")
    if not df.empty:
        history_df = df[df["status"].isin(["pass", "saturated"])]
        if history_df.empty:
            st.info("No historical exclusions yet.")
        else:
            st.dataframe(history_df[["name", "status", "notes", "last_updated"]])

    st.subheader("Error Logs")
    log_path = DB_PATH.parent / "scraper.log"
    if log_path.exists():
        st.download_button("Download Log", data=log_path.read_text(encoding="utf-8"), file_name="scraper.log")
        st.text(log_path.read_text(encoding="utf-8")[-4000:])
    else:
        st.info("No errors logged yet.")


if __name__ == "__main__":
    main()

