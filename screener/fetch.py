"""All network I/O against Yahoo Finance via yfinance, with Streamlit caching.

Everything here is wrapped in try/except and degrades to ``NaN`` / empty frames
so the UI never crashes on a throttled or missing ticker. Caching TTLs encode
the "live prices, cached fundamentals" model:

* prices        -> short TTL (seconds)   -> feels near-real-time
* fundamentals  -> long TTL (minutes)    -> slow & rate-limited, changes rarely
* financials    -> long TTL (minutes)    -> annual/quarterly statements
"""
from __future__ import annotations

import math
from typing import Iterable

import pandas as pd
import streamlit as st
import yfinance as yf

PRICE_TTL = 45          # seconds
FUNDAMENTALS_TTL = 900  # 15 minutes
FINANCIALS_TTL = 900    # 15 minutes


# --------------------------------------------------------------------------- #
# Prices (fast, short cache)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=PRICE_TTL, show_spinner=False)
def get_prices(tickers: tuple[str, ...]) -> dict[str, float]:
    """Return {ticker: latest_close} for the given tickers in one batch call."""
    if not tickers:
        return {}
    prices: dict[str, float] = {}
    try:
        data = yf.download(
            list(tickers),
            period="1d",
            interval="1m",
            progress=False,
            group_by="ticker",
            threads=True,
            auto_adjust=False,
        )
    except Exception:
        return {t: math.nan for t in tickers}

    for t in tickers:
        try:
            if len(tickers) == 1:
                close = data["Close"]
            else:
                close = data[t]["Close"]
            close = close.dropna()
            prices[t] = float(close.iloc[-1]) if len(close) else math.nan
        except Exception:
            prices[t] = math.nan
    return prices


# --------------------------------------------------------------------------- #
# Fundamentals (slow, long cache) — one .info call per ticker
# --------------------------------------------------------------------------- #
def _one_fundamentals(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    def num(*keys):
        for k in keys:
            v = info.get(k)
            if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
                return float(v)
        return math.nan

    roe = num("returnOnEquity")
    return {
        "price": num("currentPrice", "regularMarketPrice", "previousClose"),
        "pe": num("trailingPE"),
        "market_cap": num("marketCap"),
        "roe": roe * 100 if not math.isnan(roe) else math.nan,  # -> percent
        "sector": info.get("sector") or "—",
        "long_name": info.get("longName") or info.get("shortName") or "",
    }


@st.cache_data(ttl=FUNDAMENTALS_TTL, show_spinner=False)
def get_fundamentals(tickers: tuple[str, ...], _progress=None) -> pd.DataFrame:
    """Return a DataFrame indexed by ticker with fundamentals columns.

    ``_progress`` (optional) is a callback ``(done, total)`` for a progress bar;
    it is prefixed with ``_`` so Streamlit does not try to hash it for caching.
    """
    rows = {}
    total = len(tickers)
    for i, t in enumerate(tickers, start=1):
        rows[t] = _one_fundamentals(t)
        if _progress is not None:
            _progress(i, total)
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "ticker"
    return df


# --------------------------------------------------------------------------- #
# Financials for the drill-down chart (sales / profit / margins)
# --------------------------------------------------------------------------- #
def _pick_row(df: pd.DataFrame, *candidates: str) -> pd.Series | None:
    for c in candidates:
        if c in df.index:
            return df.loc[c]
    return None


@st.cache_data(ttl=FINANCIALS_TTL, show_spinner=False)
def get_financials(ticker: str, period: str = "annual") -> pd.DataFrame:
    """Return a tidy DataFrame of sales/profit/margins over time.

    period: "annual" or "quarterly". Columns:
        period_label, revenue, net_income, gross_margin, operating_margin, net_margin
    Ordered oldest -> newest. Empty DataFrame if nothing is available.
    """
    empty = pd.DataFrame(
        columns=[
            "period_label", "revenue", "net_income",
            "gross_margin", "operating_margin", "net_margin",
        ]
    )
    try:
        tk = yf.Ticker(ticker)
        fin = tk.quarterly_financials if period == "quarterly" else tk.financials
    except Exception:
        return empty
    if fin is None or fin.empty:
        return empty

    revenue = _pick_row(fin, "Total Revenue", "TotalRevenue", "Operating Revenue")
    net_income = _pick_row(fin, "Net Income", "NetIncome", "Net Income Common Stockholders")
    gross_profit = _pick_row(fin, "Gross Profit", "GrossProfit")
    op_income = _pick_row(fin, "Operating Income", "OperatingIncome", "EBIT")

    if revenue is None:
        return empty

    cols = list(revenue.index)  # Timestamps, newest first
    records = []
    for c in cols:
        rev = float(revenue.get(c, math.nan))
        ni = float(net_income.get(c, math.nan)) if net_income is not None else math.nan
        gp = float(gross_profit.get(c, math.nan)) if gross_profit is not None else math.nan
        oi = float(op_income.get(c, math.nan)) if op_income is not None else math.nan

        def margin(numer):
            if rev and not math.isnan(rev) and rev != 0 and not math.isnan(numer):
                return numer / rev * 100
            return math.nan

        try:
            label = pd.Timestamp(c).strftime("%b %Y" if period == "quarterly" else "%Y")
        except Exception:
            label = str(c)

        records.append({
            "period_label": label,
            "revenue": rev,
            "net_income": ni,
            "gross_margin": margin(gp),
            "operating_margin": margin(oi),
            "net_margin": margin(ni),
        })

    out = pd.DataFrame(records)
    return out.iloc[::-1].reset_index(drop=True)  # oldest -> newest
