# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this project is

A **near-real-time stock screener** with a Streamlit web UI. The user picks a
market — **Indian NSE (Nifty 500)** or **US NYSE** — and the app fetches live
quotes and fundamentals via [`yfinance`](https://pypi.org/project/yfinance/),
filters the universe by **P/E ratio, market cap, price, and ROE** using
interactive sliders, and shows a **ranked table** of the top matches. Clicking a
row opens a drill-down panel with a **sales / profit / margins** chart
(annual or quarterly, toggleable).

## Layout

```
app.py                     # Streamlit entry point (the whole UI)
screener/
  __init__.py
  universe.py              # Loads ticker universes from data/*.csv; market metadata
  fetch.py                 # yfinance access: prices, fundamentals, financials (cached)
  screen.py                # Filtering + ranking logic (pure, no network -> unit-testable)
data/
  nifty500.csv             # NSE tickers (symbol,name) — Yahoo suffix .NS added at load
  us_nyse.csv              # US tickers (symbol,name)
scripts/
  update_nifty500.py       # Refresh data/nifty500.csv from NSE's official archive
.streamlit/config.toml     # Port (8501) + dark theme
requirements.txt
```

## Running

```bash
pip install -r requirements.txt
streamlit run app.py          # serves on http://localhost:8501
```

## Data / caching model (important)

- **Prices** refresh on a short cadence (default 60s) via `streamlit-autorefresh`;
  cached with a short TTL (`fetch.get_prices`, `ttl≈45s`).
- **Fundamentals** (P/E, market cap, ROE, sector) are slow and heavily
  rate-limited by Yahoo (~one HTTP call per ticker), so they are cached with a
  long TTL (`fetch.get_fundamentals`, `ttl≈900s`) and fetched with a progress bar.
- The **scan size** slider caps how many tickers are pulled, to stay under
  Yahoo's rate limits. Scanning the full 500 can take minutes on first load.
- All fetches are wrapped in try/except and degrade gracefully to `NaN`.

## Network constraint (Claude Code web/cloud sessions)

The managed cloud sandbox's egress policy **blocks Yahoo Finance and NSE**
(`query1.finance.yahoo.com`, `nseindia.com` → 403), so `yfinance` **cannot
fetch live data from inside a cloud session**. Code can be written, imported,
and unit-tested there, but the app must be **run on the user's own machine** to
pull real data. `screener/screen.py` is deliberately network-free so ranking
logic stays testable in the sandbox.

## Conventions

- Currency symbol and Yahoo ticker suffix come from `universe.MARKETS`
  (`.NS` for NSE / ₹, none for US / $) — never hardcode them in the UI.
- Keep `screen.py` pure (DataFrame in → DataFrame out). Put all I/O in `fetch.py`.
- yfinance `.info` keys used: `trailingPE`, `marketCap`, `returnOnEquity`,
  `regularMarketPrice`/`currentPrice`, `sector`, `longName`. Treat every key as
  optional.
