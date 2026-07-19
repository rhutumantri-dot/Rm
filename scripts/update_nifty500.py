"""Refresh data/nifty500.csv with the full official Nifty 500 constituents.

The bundled data/nifty500.csv ships with a large curated subset so the app
works out of the box. Run this on a machine that can reach nseindia.com to
replace it with the complete, current official list (~500 tickers).

    python scripts/update_nifty500.py

Requires: requests
"""
from __future__ import annotations

import io
import os
import sys

import pandas as pd
import requests

URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nifty500.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; stock-screener/1.0)",
    "Accept": "text/csv,*/*",
}


def main() -> int:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"Failed to download Nifty 500 list: {e}", file=sys.stderr)
        print("Are you on a network that can reach nseindia.com?", file=sys.stderr)
        return 1

    raw = pd.read_csv(io.StringIO(resp.text))
    # Official columns include "Symbol" and "Company Name".
    sym_col = next(c for c in raw.columns if c.strip().lower() == "symbol")
    name_col = next((c for c in raw.columns if "company" in c.strip().lower()), sym_col)

    out = pd.DataFrame({
        "symbol": raw[sym_col].astype(str).str.strip(),
        "name": raw[name_col].astype(str).str.strip(),
    })
    out = out[out["symbol"] != ""].drop_duplicates("symbol").reset_index(drop=True)
    out.to_csv(OUT, index=False)
    print(f"Wrote {len(out)} tickers to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
