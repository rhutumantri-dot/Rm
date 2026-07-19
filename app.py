"""A Streamlit stock screener.

Filter a universe of equities by sector, market cap, valuation, price, and
yield, then inspect and download the matches.

Run locally with:
    pip install -r requirements.txt
    SCREENER_DEMO=1 streamlit run app.py
    # open http://localhost:8501

Set SCREENER_DEMO=1 to run against a reproducible, generated demo universe
(no external data source required). Without it, the app looks for a live
data provider and, finding none configured here, falls back to demo data
with a notice.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Stock Screener",
    page_icon="📊",
    layout="wide",
)

SECTORS = [
    "Technology",
    "Healthcare",
    "Financials",
    "Consumer",
    "Energy",
    "Industrials",
    "Utilities",
    "Materials",
]


def _demo_enabled() -> bool:
    return os.environ.get("SCREENER_DEMO", "").strip().lower() in {"1", "true", "yes", "on"}


@st.cache_data
def load_universe(seed: int = 7, n: int = 80) -> pd.DataFrame:
    """Generate a reproducible demo universe of equities."""
    rng = np.random.default_rng(seed)

    # Build plausible-looking synthetic tickers (e.g. "TKM", "ZQP").
    letters = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    tickers: list[str] = []
    seen: set[str] = set()
    while len(tickers) < n:
        length = int(rng.integers(3, 5))
        sym = "".join(rng.choice(letters, size=length))
        if sym not in seen:
            seen.add(sym)
            tickers.append(sym)

    price = np.round(rng.uniform(5, 500, size=n), 2)
    # Market cap in billions, log-spread so a few mega caps exist.
    market_cap_b = np.round(np.exp(rng.uniform(np.log(0.5), np.log(2500), size=n)), 2)
    pe = np.round(rng.uniform(5, 60, size=n), 1)
    div_yield = np.round(np.clip(rng.normal(1.8, 1.4, size=n), 0, None), 2)
    change_52w = np.round(rng.normal(8, 30, size=n), 1)
    sector = rng.choice(SECTORS, size=n)

    return pd.DataFrame(
        {
            "Ticker": tickers,
            "Sector": sector,
            "Price": price,
            "Market Cap ($B)": market_cap_b,
            "P/E": pe,
            "Div Yield (%)": div_yield,
            "52W Change (%)": change_52w,
        }
    ).sort_values("Market Cap ($B)", ascending=False, ignore_index=True)


def main() -> None:
    demo = _demo_enabled()

    st.title("📊 Stock Screener")
    if demo:
        st.caption("Running on a reproducible **demo** universe (`SCREENER_DEMO=1`).")
    else:
        st.warning(
            "No live data provider is configured in this build, so the screener "
            "is showing generated demo data. Set `SCREENER_DEMO=1` to make this "
            "explicit, or wire up a data source in `load_universe()`.",
            icon="⚠️",
        )

    df = load_universe()

    # ---- Sidebar filters ------------------------------------------------
    with st.sidebar:
        st.header("Filters")

        query = st.text_input("Search ticker", placeholder="e.g. ABC").strip().upper()

        sectors = st.multiselect("Sector", SECTORS, default=SECTORS)

        cap_min, cap_max = float(df["Market Cap ($B)"].min()), float(df["Market Cap ($B)"].max())
        cap_range = st.slider(
            "Market cap ($B)",
            min_value=0.0,
            max_value=float(np.ceil(cap_max)),
            value=(0.0, float(np.ceil(cap_max))),
        )

        price_max = float(np.ceil(df["Price"].max()))
        price_range = st.slider("Price ($)", 0.0, price_max, (0.0, price_max))

        pe_max = float(np.ceil(df["P/E"].max()))
        pe_range = st.slider("P/E ratio", 0.0, pe_max, (0.0, pe_max))

        min_yield = st.slider("Min dividend yield (%)", 0.0, 8.0, 0.0, step=0.1)

    # ---- Apply filters --------------------------------------------------
    mask = (
        df["Sector"].isin(sectors)
        & df["Market Cap ($B)"].between(*cap_range)
        & df["Price"].between(*price_range)
        & df["P/E"].between(*pe_range)
        & (df["Div Yield (%)"] >= min_yield)
    )
    if query:
        mask &= df["Ticker"].str.contains(query, na=False)

    results = df[mask].reset_index(drop=True)

    # ---- Summary metrics ------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matches", f"{len(results)}", f"of {len(df)}")
    c2.metric("Total mkt cap", f"${results['Market Cap ($B)'].sum():,.0f}B")
    c3.metric("Avg P/E", f"{results['P/E'].mean():.1f}" if len(results) else "—")
    c4.metric(
        "Avg yield",
        f"{results['Div Yield (%)'].mean():.2f}%" if len(results) else "—",
    )

    if results.empty:
        st.info("No stocks match the current filters. Loosen them in the sidebar.")
        return

    # ---- Results table --------------------------------------------------
    st.subheader("Results")
    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "Market Cap ($B)": st.column_config.NumberColumn(format="%.2f"),
            "Div Yield (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "52W Change (%)": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.download_button(
        "Download results (CSV)",
        results.to_csv(index=False).encode("utf-8"),
        file_name="screener_results.csv",
        mime="text/csv",
    )

    # ---- Breakdown chart ------------------------------------------------
    st.subheader("Market cap by sector")
    by_sector = (
        results.groupby("Sector")["Market Cap ($B)"].sum().sort_values(ascending=False)
    )
    st.bar_chart(by_sector)


if __name__ == "__main__":
    main()
