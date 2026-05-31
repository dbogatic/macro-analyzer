from __future__ import annotations

import datetime

import pandas as pd
import requests

_YF_URL = "https://query1.finance.yahoo.com/v8/finance/chart/GLD"
_HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_gld_history(start: str, end: str) -> pd.Series | None:
    """
    Fetch GLD daily close prices for a date range as a pandas Series.
    start / end: 'YYYY-MM-DD' strings.
    Returns None on any failure — callers should handle gracefully.
    """
    start_dt = datetime.datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end, "%Y-%m-%d")
    params = {
        "interval": "1d",
        "period1": int(start_dt.timestamp()),
        "period2": int(end_dt.timestamp()),
    }
    try:
        resp = requests.get(_YF_URL, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        index = pd.to_datetime(timestamps, unit="s").normalize()
        series = pd.Series(closes, index=index, dtype=float).dropna()
        series.index = series.index.tz_localize(None)
        return series
    except Exception:
        return None


def get_gld_data() -> tuple[float | None, float | None, str | None]:
    """
    Fetch GLD (SPDR Gold ETF) via Yahoo Finance JSON API.
    Returns (yoy_pct, spot_price_usd, error_message).
    GLD ≈ 1/10 troy oz of gold, so spot price = GLD close * 10.
    Uses direct HTTP request — no yfinance library, no API key required.
    """
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GLD"
    params = {"interval": "1d", "range": "2y"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 252:
            return None, None, f"Only {len(closes)} trading days returned (need 252)"
        yoy = (closes[-1] / closes[-252] - 1) * 100
        spot_price = round(closes[-1] * 10, 0)   # approximate gold spot ($/oz)
        return round(float(yoy), 2), spot_price, None
    except Exception as e:
        return None, None, str(e)


def get_gld_yoy() -> tuple[float | None, str | None]:
    """Thin wrapper for backward compatibility — returns (yoy_pct, error)."""
    yoy, _, error = get_gld_data()
    return yoy, error
