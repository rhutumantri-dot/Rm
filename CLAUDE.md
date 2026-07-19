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

An **offline demo mode** (`SCREENER_DEMO=1`) renders the whole app with
deterministic synthetic data, so it works on machines that cannot reach Yahoo
Finance.

## Layout

```
app.py                     # Streamlit entry point (the whole UI)
screener/
  __init__.py
  universe.py              # Loads ticker universes from data/*.csv; market metadata
  fetch.py                 # yfinance access: prices, fundamentals, financials (cached)
  screen.py                # Filtering + ranking logic (pure, no network -> unit-testable)
  demo.py                  # Deterministic synthetic data for SCREENER_DEMO offline mode
data/
  nifty500.csv             # NSE tickers (symbol,name) — Yahoo suffix .NS added at load
  us_nyse.csv              # US tickers (symbol,name)
scripts/
  update_nifty500.py       # Refresh data/nifty500.csv from NSE's official archive
.streamlit/config.toml     # Port (8501), headless, dark theme
requirements.txt
```

## Running

```bash
pip install -r requirements.txt
streamlit run app.py                    # serves on http://localhost:8501
SCREENER_DEMO=1 streamlit run app.py    # offline demo with synthetic data (no network)
```

## Architecture

The app is a thin Streamlit script over a small, layered package:

- **`app.py`** — all UI: sidebar controls, auto-refresh, the ranked table, and
  the drill-down chart. It orchestrates fetch → screen → render and holds the
  per-market slider config (`FILTER_CFG`) and display formatting helpers.
- **`screener/universe.py`** — the `Market` dataclass and the `MARKETS` registry
  (currency symbol + Yahoo suffix per market). `load_universe(market)` reads the
  CSV and produces `symbol`, `name`, `ticker` columns.
- **`screener/fetch.py`** — the only place that touches the network. Three cached
  entry points: `get_prices`, `get_fundamentals`, `get_financials`. Routes to
  `demo.py` when `SCREENER_DEMO` is set.
- **`screener/screen.py`** — pure DataFrame-in/DataFrame-out `apply_filters` and
  `rank`. No network, no Streamlit → unit-testable anywhere.
- **`screener/demo.py`** — deterministic synthetic prices/fundamentals/financials
  keyed off the ticker string, with a small time-based wobble on prices.

Data flow per run: `load_universe` → `get_fundamentals` (long cache) →
`get_prices` (short cache, overrides the fundamentals price snapshot) →
`apply_filters` → `rank` → table → optional `get_financials` on row-click.

## Data / caching model (important)

- **Prices** refresh on a short cadence (default 60s in the UI) via
  `streamlit-autorefresh`; cached with a short TTL (`fetch.PRICE_TTL ≈ 45s`).
- **Fundamentals** (P/E, market cap, ROE, sector) are slow and heavily
  rate-limited by Yahoo (~one HTTP `.info` call per ticker), so they are cached
  per-ticker with a long TTL (`fetch.FUNDAMENTALS_TTL = 900s`) and fetched with a
  progress bar. `get_fundamentals` itself is *not* cached — it fans out to the
  cached `_fundamentals_one`, so reruns are cheap but a fresh scan still fills in
  one ticker at a time.
- **Financials** for the drill-down chart are cached with a long TTL
  (`fetch.FINANCIALS_TTL = 900s`).
- The **scan size** slider caps how many tickers are pulled, to stay under
  Yahoo's rate limits. Scanning the full universe can take minutes on first load.
- All fetches are wrapped in try/except and degrade gracefully to `NaN` / empty
  frames so the UI never crashes on a throttled or missing ticker.
- The **progress callback** is invoked in `get_fundamentals` (the caller's
  Streamlit context), never inside a `@st.cache_data` function — doing so would
  raise `CacheReplayClosureError`.

## Network constraint (Claude Code web/cloud sessions)

The managed cloud sandbox's egress policy **blocks Yahoo Finance and NSE**
(`query1.finance.yahoo.com`, `nseindia.com` → 403), so `yfinance` **cannot
fetch live data from inside a cloud session**. Code can be written, imported,
and unit-tested there, but the app must be **run on the user's own machine** to
pull real data. Two things keep development possible in the sandbox:

- `screener/screen.py` is deliberately network-free, so ranking logic stays
  testable in the sandbox.
- `SCREENER_DEMO=1` renders the full UI with synthetic data, so the app can be
  demoed end-to-end without any network.

## Conventions

- Currency symbol and Yahoo ticker suffix come from `universe.MARKETS`
  (`.NS` for NSE / ₹, none for US / $) — never hardcode them in the UI.
- Keep `screen.py` pure (DataFrame in → DataFrame out). Put all I/O in `fetch.py`.
- Any new source of data (live or demo) must produce the same column schema the
  rest of the app expects:
  - fundamentals: `price`, `pe`, `market_cap`, `roe` (percent), `sector`, `long_name`
  - financials: `period_label`, `revenue`, `net_income`, `gross_margin`,
    `operating_margin`, `net_margin` (ordered oldest → newest)
- When adding a code path that hits the network, also add a matching branch in
  `demo.py` and route to it via `_demo_mode()` in `fetch.py`.
- yfinance `.info` keys used: `trailingPE`, `marketCap`, `returnOnEquity`,
  `currentPrice`/`regularMarketPrice`/`previousClose`, `sector`,
  `longName`/`shortName`. Treat every key as optional.
- ROE is stored/displayed as a percentage; market cap and financials are in the
  market's local currency.

## Ticker universes

- `data/*.csv` are plain `symbol,name` files. NSE symbols get the Yahoo `.NS`
  suffix appended at load time; US symbols are used as-is.
- The bundled `data/nifty500.csv` is a curated subset (works out of the box);
  run `python scripts/update_nifty500.py` on a network that can reach
  `nseindia.com` to replace it with the full official list.
