"""Ticker universes and per-market metadata.

Loads the list of candidate tickers for each supported market from the CSV
files in ``data/`` and exposes the currency symbol and Yahoo ticker suffix so
the rest of the app never has to hardcode them.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@dataclass(frozen=True)
class Market:
    key: str            # internal id
    label: str          # shown in the UI
    csv: str            # filename under data/
    yahoo_suffix: str   # appended to each symbol for Yahoo Finance (e.g. ".NS")
    currency: str       # display symbol


MARKETS: dict[str, Market] = {
    "nse": Market(
        key="nse",
        label="🇮🇳 India · NSE (Nifty 500)",
        csv="nifty500.csv",
        yahoo_suffix=".NS",
        currency="₹",
    ),
    "us": Market(
        key="us",
        label="🇺🇸 US · NYSE",
        csv="us_nyse.csv",
        yahoo_suffix="",
        currency="$",
    ),
}


def load_universe(market: Market) -> pd.DataFrame:
    """Return a DataFrame with columns: symbol, name, ticker.

    ``symbol`` is the raw exchange symbol, ``ticker`` is the Yahoo Finance
    ticker (symbol + market suffix).
    """
    path = os.path.join(_DATA_DIR, market.csv)
    df = pd.read_csv(path, dtype=str).fillna("")
    df["symbol"] = df["symbol"].str.strip()
    df["name"] = df["name"].str.strip()
    df = df[df["symbol"] != ""].drop_duplicates(subset="symbol").reset_index(drop=True)
    df["ticker"] = df["symbol"] + market.yahoo_suffix
    return df
