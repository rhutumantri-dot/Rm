"""Deterministic synthetic data for offline demos.

Enabled when the env var ``SCREENER_DEMO=1`` is set. Lets the whole app render
with realistic-looking numbers on a machine that cannot reach Yahoo Finance
(e.g. a locked-down sandbox), without changing any UI code.

Everything is derived deterministically from the ticker string (plus a small
time-based jitter for prices) so the screen looks stable but "live".
"""
from __future__ import annotations

import hashlib
import math
import time

_SECTORS = [
    "Financials", "Information Technology", "Energy", "Consumer Staples",
    "Health Care", "Industrials", "Materials", "Consumer Discretionary",
    "Utilities", "Communication Services",
]


def _seed(ticker: str) -> int:
    return int(hashlib.md5(ticker.encode()).hexdigest(), 16)


def _frac(ticker: str, salt: str) -> float:
    """Deterministic float in [0, 1) for a ticker + salt."""
    h = hashlib.md5(f"{ticker}:{salt}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def base_price(ticker: str) -> float:
    is_nse = ticker.endswith(".NS")
    lo, hi = (80, 8000) if is_nse else (30, 900)
    return round(lo + _frac(ticker, "price") * (hi - lo), 2)


def fundamentals(ticker: str) -> dict:
    price = base_price(ticker)
    is_nse = ticker.endswith(".NS")
    unit = 1e9 if is_nse else 1e9
    market_cap = round((5 + _frac(ticker, "mcap") * 300) * unit)  # 5–305 bn
    return {
        "price": price,
        "pe": round(8 + _frac(ticker, "pe") * 42, 1),          # 8–50
        "market_cap": float(market_cap),
        "roe": round(5 + _frac(ticker, "roe") * 33, 1),        # 5–38 %
        "sector": _SECTORS[_seed(ticker) % len(_SECTORS)],
        "long_name": "",
    }


def live_price(ticker: str) -> float:
    """Base price with a small, time-varying wobble so refresh feels live."""
    base = base_price(ticker)
    phase = _frac(ticker, "phase") * math.tau
    wobble = math.sin(time.time() / 20 + phase) * 0.01  # ±1%
    return round(base * (1 + wobble), 2)


def financials(ticker: str, period: str = "annual") -> list[dict]:
    """Return oldest->newest records matching fetch.get_financials' schema."""
    n = 6 if period == "quarterly" else 4
    is_nse = ticker.endswith(".NS")
    scale = 1e10 if is_nse else 1e9  # revenue magnitude
    rev0 = (2 + _frac(ticker, "rev") * 20) * scale
    growth = 1.03 + _frac(ticker, "growth") * 0.12          # 3–15% per period
    net_margin = 0.05 + _frac(ticker, "nm") * 0.22          # 5–27%
    gross_margin = net_margin + 0.15 + _frac(ticker, "gm") * 0.15
    op_margin = net_margin + 0.05 + _frac(ticker, "om") * 0.08

    now = time.localtime()
    records = []
    for i in range(n):
        step = n - 1 - i  # older periods first
        rev = rev0 * (growth ** i)
        if period == "quarterly":
            # Count months back from the current month, handling year wrap.
            mi = (now.tm_year * 12 + (now.tm_mon - 1)) - step * 3
            year, month = divmod(mi, 12)
            label = time.strftime("%b %Y", time.struct_time(
                (year, month + 1, 1, 0, 0, 0, 0, 0, 0)))
            rev /= 4
        else:
            label = str(now.tm_year - 1 - step)
        records.append({
            "period_label": label,
            "revenue": rev,
            "net_income": rev * net_margin,
            "gross_margin": gross_margin * 100,
            "operating_margin": op_margin * 100,
            "net_margin": net_margin * 100,
        })
    return records
