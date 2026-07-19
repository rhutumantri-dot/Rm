# Stock Screener

A [Streamlit](https://streamlit.io) stock screener. Filter a universe of
equities by sector, market cap, valuation (P/E), price, and dividend yield,
then inspect and download the matches.

## Getting started

```bash
pip install -r requirements.txt
SCREENER_DEMO=1 streamlit run app.py
# open http://localhost:8501
```

`SCREENER_DEMO=1` runs the app against a reproducible, generated demo
universe — no external data source required. Without it, the app falls back
to demo data and shows a notice, since no live data provider is wired up in
this build.

## What's included

- `app.py` — the screener: sidebar filters (search, sector, market cap,
  price, P/E, min yield), summary metrics, a sortable/formatted results
  table, a CSV download, and a market-cap-by-sector chart.
- `requirements.txt` — pinned minimum versions for Streamlit, pandas, numpy.
- `.gitignore` — common Python/Streamlit ignores.

## Wiring up live data

Replace the body of `load_universe()` in `app.py` with a call to your data
provider, returning a DataFrame with the same columns.
