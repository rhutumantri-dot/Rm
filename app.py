"""Near-real-time stock screener — Streamlit UI.

Pick a market (NSE Nifty 500 or US NYSE), filter by P/E / market cap / price /
ROE with live sliders, see a ranked table that refreshes on a timer, and click
any row to drill into its sales / profit / margins chart.

Run:  streamlit run app.py   ->  http://localhost:8501
"""
from __future__ import annotations

import math
import time

import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from screener import fetch, screen
from screener.universe import MARKETS, load_universe

st.set_page_config(page_title="Stock Screener · Live", page_icon="📈", layout="wide")

# --------------------------------------------------------------------------- #
# Per-market slider configuration (local-currency scales differ a lot)
# --------------------------------------------------------------------------- #
FILTER_CFG = {
    "nse": dict(price_max=200_000, price_default=(0, 200_000),
                mcap_max_bn=25_000, mcap_unit="₹ bn"),
    "us":  dict(price_max=10_000, price_default=(0, 10_000),
                mcap_max_bn=4_000, mcap_unit="$ bn"),
}


def human_money(v: float, currency: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e7, "Cr"), (1e6, "M")):
        if a >= div:
            return f"{currency}{v/div:,.2f}{suf}"
    return f"{currency}{v:,.0f}"


# --------------------------------------------------------------------------- #
# Sidebar — controls
# --------------------------------------------------------------------------- #
st.sidebar.title("📈 Screener controls")

market_key = st.sidebar.selectbox(
    "Market",
    options=list(MARKETS.keys()),
    format_func=lambda k: MARKETS[k].label,
)
market = MARKETS[market_key]
cfg = FILTER_CFG[market_key]

universe = load_universe(market)
max_scan = len(universe)

st.sidebar.caption(f"{max_scan} tickers available in this universe.")
scan_n = st.sidebar.slider(
    "Stocks to scan",
    min_value=min(10, max_scan), max_value=max_scan,
    value=min(60, max_scan), step=10,
    help="Fundamentals are fetched one-by-one from Yahoo and rate-limited. "
         "Start small; the full list can take minutes on first load.",
)

st.sidebar.divider()
live = st.sidebar.toggle("🔴 Live prices", value=True,
                         help="Auto-refresh prices on a timer.")
refresh_secs = st.sidebar.slider("Refresh every (seconds)", 15, 300, 60, step=15,
                                 disabled=not live)

st.sidebar.divider()
st.sidebar.subheader("Filters")
pe_range = st.sidebar.slider("P/E ratio", 0.0, 150.0, (0.0, 40.0), step=0.5)
price_range = st.sidebar.slider(
    f"Price ({market.currency})", 0.0, float(cfg["price_max"]),
    (0.0, float(cfg["price_max"])), step=float(cfg["price_max"]) / 200,
)
mcap_min_bn = st.sidebar.slider(
    f"Min market cap ({cfg['mcap_unit']})", 0.0, float(cfg["mcap_max_bn"]),
    0.0, step=float(cfg["mcap_max_bn"]) / 200,
)
roe_min = st.sidebar.slider("Min ROE (%)", -50.0, 100.0, 0.0, step=1.0)

st.sidebar.divider()
rank_by = st.sidebar.selectbox(
    "Rank by",
    options=["composite", "roe", "pe", "market_cap", "price"],
    format_func=lambda k: {
        "composite": "Composite (value + quality)",
        "roe": "ROE (high → low)",
        "pe": "P/E (low → high)",
        "market_cap": "Market cap (large → small)",
        "price": "Price (high → low)",
    }[k],
)
top_n = st.sidebar.slider("Show top N", 5, 100, 25, step=5)

# --------------------------------------------------------------------------- #
# Auto-refresh (only re-runs the script; fundamentals stay cached, prices don't)
# --------------------------------------------------------------------------- #
if live:
    st_autorefresh(interval=refresh_secs * 1000, key="price_refresh")

# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
scan = universe.head(scan_n).copy()
tickers = tuple(scan["ticker"].tolist())

# Fundamentals (long cache) with a progress bar on cache-miss.
prog = st.sidebar.progress(0.0, text="Loading fundamentals…")


def _update(done, total):
    prog.progress(done / total, text=f"Loading fundamentals… {done}/{total}")


fund = fetch.get_fundamentals(tickers, progress_cb=_update)
prog.empty()

# Live prices (short cache) overwrite the fundamentals' price snapshot.
prices = fetch.get_prices(tickers)

merged = scan.set_index("ticker").join(fund)
merged["price"] = pd.Series(prices).reindex(merged.index).fillna(merged["price"])

filtered = screen.apply_filters(
    merged,
    pe_range=(pe_range[0], pe_range[1]),
    price_range=(price_range[0], price_range[1]),
    mcap_min=mcap_min_bn * 1e9,
    roe_min=roe_min,
)
ranked = screen.rank(filtered, by=rank_by, top_n=top_n)

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
left, right = st.columns([3, 1])
with left:
    st.title("Live Stock Screener")
    st.caption(f"{market.label}  ·  scanning {len(scan)} of {max_scan} tickers  ·  "
               f"{len(filtered)} pass filters")
with right:
    st.metric("Last updated", time.strftime("%H:%M:%S"))
    if live:
        st.caption(f"🔴 auto-refresh every {refresh_secs}s")

# --------------------------------------------------------------------------- #
# Ranked table (click a row to drill in)
# --------------------------------------------------------------------------- #
if ranked.empty:
    st.warning("No stocks match the current filters. Loosen the sliders on the left. "
               "(If every metric is blank, Yahoo Finance may be unreachable from this "
               "network — run the app on your own machine.)")
    st.stop()

display = pd.DataFrame({
    "Rank": ranked["rank"],
    "Symbol": ranked["symbol"],
    "Name": ranked["name"],
    "Sector": ranked["sector"],
    "Price": ranked["price"],
    "P/E": ranked["pe"],
    "ROE %": ranked["roe"],
    "Market Cap": ranked["market_cap"],
})

st.subheader("Ranked results")
event = st.dataframe(
    display,
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Price": st.column_config.NumberColumn(format=f"{market.currency}%.2f"),
        "P/E": st.column_config.NumberColumn(format="%.1f"),
        "ROE %": st.column_config.NumberColumn(format="%.1f%%"),
        "Market Cap": st.column_config.NumberColumn(
            format="compact",
            help=f"In {market.currency}",
        ),
    },
)

# --------------------------------------------------------------------------- #
# Drill-down: sales / profit / margins
# --------------------------------------------------------------------------- #
sel_rows = event.selection.rows if event and event.selection else []
if not sel_rows:
    st.info("👆 Click a row above to see that company's sales, profit and margins.")
    st.stop()

row = ranked.iloc[sel_rows[0]]
st.divider()
head_l, head_r = st.columns([3, 1])
with head_l:
    st.subheader(f"{row['symbol']} — {row['name']}")
    st.caption(f"{row['sector']}  ·  P/E {row['pe']:.1f}  ·  ROE {row['roe']:.1f}%  ·  "
               f"Mkt cap {human_money(row['market_cap'], market.currency)}")
with head_r:
    st.metric("Price", human_money(row["price"], market.currency))

period_label = st.radio(
    "Financials period", ["Annual", "Quarterly"], horizontal=True,
    key=f"period_{row['ticker']}",
)
period = "quarterly" if period_label == "Quarterly" else "annual"

fin = fetch.get_financials(row["ticker"], period=period)
if fin.empty:
    st.warning("No financial statement data available for this ticker from Yahoo Finance.")
    st.stop()

# Scale money to a readable unit.
max_val = pd.concat([fin["revenue"], fin["net_income"]]).abs().max()
if max_val >= 1e12:
    div, unit = 1e12, "T"
elif max_val >= 1e9:
    div, unit = 1e9, "B"
elif max_val >= 1e7:
    div, unit = 1e7, "Cr"
else:
    div, unit = 1e6, "M"

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_bar(x=fin["period_label"], y=fin["revenue"] / div,
            name="Sales (Revenue)", marker_color="#3b82f6")
fig.add_bar(x=fin["period_label"], y=fin["net_income"] / div,
            name="Net Profit", marker_color="#22c55e")
for col, name, color in [
    ("gross_margin", "Gross margin", "#f59e0b"),
    ("operating_margin", "Operating margin", "#a855f7"),
    ("net_margin", "Net margin", "#ef4444"),
]:
    if fin[col].notna().any():
        fig.add_scatter(x=fin["period_label"], y=fin[col], name=name,
                        mode="lines+markers", line=dict(color=color, width=2),
                        secondary_y=True)

fig.update_layout(
    barmode="group",
    height=460,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(t=40, b=40, l=10, r=10),
    template="plotly_dark",
)
fig.update_yaxes(title_text=f"{market.currency} ({unit})", secondary_y=False)
fig.update_yaxes(title_text="Margin (%)", secondary_y=True, showgrid=False)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Show underlying numbers"):
    tbl = fin.copy()
    tbl["revenue"] = tbl["revenue"].map(lambda v: human_money(v, market.currency))
    tbl["net_income"] = tbl["net_income"].map(lambda v: human_money(v, market.currency))
    for c in ("gross_margin", "operating_margin", "net_margin"):
        tbl[c] = tbl[c].map(lambda v: "—" if pd.isna(v) else f"{v:.1f}%")
    tbl.columns = ["Period", "Revenue", "Net income",
                   "Gross margin", "Operating margin", "Net margin"]
    st.dataframe(tbl, hide_index=True, use_container_width=True)
