# 📈 Live Stock Screener — NSE Nifty 500 / US NYSE

A near-real-time stock screener with a Streamlit web UI. Pick a market, filter
by **P/E, market cap, price, and ROE** with live sliders, get a **ranked table**
of the top matches, and **click any stock** to drill into a **sales / profit /
margins** chart (annual or quarterly).

Data comes from Yahoo Finance via [`yfinance`](https://pypi.org/project/yfinance/).

---

## Quick start

```bash
# 1. install dependencies (a virtualenv is recommended)
pip install -r requirements.txt

# 2. run the app
streamlit run app.py
```

Then open **http://localhost:8501** in your browser (the port is set in
`.streamlit/config.toml` — change it there or with `--server.port`).

> **Run this on your own machine / a network with internet access.** yfinance
> needs to reach Yahoo Finance. Locked-down/cloud sandboxes that block
> `query1.finance.yahoo.com` (or NSE) will show blank metrics.

---

## Using it

- **Market** — switch between 🇮🇳 NSE (Nifty 500) and 🇺🇸 NYSE in the sidebar.
- **Stocks to scan** — how many tickers to pull fundamentals for. Yahoo
  rate-limits per-ticker calls, so start with 40–60; the full universe can take
  minutes on the first load, then it's cached.
- **🔴 Live prices** — auto-refreshes prices on the chosen interval. Fundamentals
  (P/E, ROE, market cap) are cached ~15 min; only prices refresh each tick.
- **Filters** — P/E, price, min market cap, and min ROE sliders re-rank instantly.
- **Rank by** — composite value+quality score, or any single metric.
- **Click a row** — opens the drill-down chart with an Annual / Quarterly toggle.

---

## Get the full Nifty 500 list

The bundled `data/nifty500.csv` contains a large curated subset so the app works
immediately. To replace it with the complete official list:

```bash
python scripts/update_nifty500.py     # needs to reach nseindia.com
```

You can also hand-edit `data/nifty500.csv` or `data/us_nyse.csv` — they're just
`symbol,name` CSVs. Yahoo's `.NS` suffix for NSE is added automatically.

---

## Project layout

| Path | Purpose |
|------|---------|
| `app.py` | Streamlit UI (sidebar, table, drill-down chart) |
| `screener/universe.py` | Loads ticker universes + per-market currency/suffix |
| `screener/fetch.py` | yfinance access (prices, fundamentals, financials) with caching |
| `screener/screen.py` | Pure filtering + ranking logic (network-free, testable) |
| `scripts/update_nifty500.py` | Refresh the Nifty 500 CSV from NSE |
| `data/*.csv` | Ticker universes |

---

## Notes & caveats

- yfinance is an unofficial Yahoo Finance scraper; fields can be missing or
  occasionally rate-limited. Missing metrics show as `—` and the app keeps working.
- Fundamentals like P/E and ROE update slowly at the source; "near real-time"
  here means **live prices** over a cached fundamentals snapshot.
- ROE is displayed as a percentage; market cap and financials are in the
  market's local currency (₹ for NSE, $ for NYSE).
