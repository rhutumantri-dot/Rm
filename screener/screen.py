"""Filtering and ranking logic.

Deliberately pure: takes a DataFrame of stock metrics and filter thresholds,
returns a filtered + ranked DataFrame. No network, no Streamlit — so it can be
unit-tested anywhere (including sandboxes where Yahoo Finance is blocked).
"""
from __future__ import annotations

import pandas as pd

# Column set the screener operates on.
METRIC_COLS = ["price", "pe", "market_cap", "roe"]


def apply_filters(
    df: pd.DataFrame,
    *,
    pe_range: tuple[float, float],
    price_range: tuple[float, float],
    mcap_min: float,
    roe_min: float,
    require_positive_pe: bool = True,
) -> pd.DataFrame:
    """Filter rows by the four screening dimensions.

    * pe_range     : inclusive (min, max) trailing P/E
    * price_range  : inclusive (min, max) current price
    * mcap_min     : minimum market cap (same units as df["market_cap"])
    * roe_min      : minimum ROE in percent
    * require_positive_pe : drop rows with non-positive / missing P/E
    """
    out = df.copy()
    mask = pd.Series(True, index=out.index)

    pe = out["pe"]
    if require_positive_pe:
        # Drop missing / non-positive P/E, then apply the range.
        mask &= pe.notna() & (pe > 0)
        mask &= pe.between(pe_range[0], pe_range[1])
    else:
        # Keep rows in range, and also keep rows with no P/E at all.
        mask &= pe.between(pe_range[0], pe_range[1]) | pe.isna()

    mask &= out["price"].between(price_range[0], price_range[1])
    mask &= out["market_cap"].fillna(0) >= mcap_min
    mask &= out["roe"].fillna(float("-inf")) >= roe_min

    return out[mask].copy()


def rank(
    df: pd.DataFrame,
    *,
    by: str = "composite",
    top_n: int | None = None,
) -> pd.DataFrame:
    """Rank filtered stocks and return the top ``top_n``.

    Sort keys:
      * "composite" – value/quality blend: high ROE, low P/E
      * "roe"       – highest ROE first
      * "pe"        – lowest P/E first
      * "market_cap"– largest first
      * "price"     – highest price first
    """
    out = df.copy()
    if out.empty:
        out["score"] = []
        return out

    if by == "composite":
        # z-score ROE (higher better) minus z-score P/E (lower better).
        def z(series, invert=False):
            s = series.astype(float)
            std = s.std(ddof=0)
            if not std or pd.isna(std):
                return pd.Series(0.0, index=s.index)
            zz = (s - s.mean()) / std
            return -zz if invert else zz

        out["score"] = z(out["roe"]).fillna(0) + z(out["pe"], invert=True).fillna(0)
        out = out.sort_values("score", ascending=False)
    elif by == "roe":
        out = out.sort_values("roe", ascending=False)
    elif by == "pe":
        out = out.sort_values("pe", ascending=True)
    elif by == "market_cap":
        out = out.sort_values("market_cap", ascending=False)
    elif by == "price":
        out = out.sort_values("price", ascending=False)
    else:
        raise ValueError(f"unknown rank key: {by}")

    out = out.reset_index()  # keep 'ticker' as a column
    out.insert(0, "rank", range(1, len(out) + 1))
    if top_n is not None:
        out = out.head(top_n)
    return out
