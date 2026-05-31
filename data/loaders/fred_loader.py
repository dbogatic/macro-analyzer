from __future__ import annotations

import time
from typing import Any

import pandas as pd
from fredapi import Fred

from config.settings import settings

# Series that return index levels and must be converted to YoY % change
YOY_SERIES = {"core_pce", "cpi", "gold"}

_TIMEOUT    = 10   # seconds per request
_MAX_TRIES  = 3    # total attempts before giving up
_RETRY_WAIT = 2    # seconds between retries


def _get_client() -> Fred:
    if not settings.fred_api_key:
        raise RuntimeError("Missing FRED_API_KEY. Add it to your .env file.")
    return Fred(api_key=settings.fred_api_key)


def _fetch_with_retry(series_id: str) -> pd.Series:
    """Fetch a FRED series with timeout and automatic retries."""
    import socket
    last_exc: Exception | None = None
    for attempt in range(_MAX_TRIES):
        try:
            socket.setdefaulttimeout(_TIMEOUT)
            return _get_client().get_series(series_id).dropna()
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_TRIES - 1:
                time.sleep(_RETRY_WAIT)
        finally:
            socket.setdefaulttimeout(None)  # restore default
    raise RuntimeError(f"FRED request failed after {_MAX_TRIES} attempts: {last_exc}")


def get_series_latest(series_id: str) -> float:
    series = _fetch_with_retry(series_id)
    if series.empty:
        raise ValueError(f"No data returned for {series_id}")
    return float(series.iloc[-1])


def get_series_yoy(series_id: str) -> float:
    """Return latest year-over-year % change for an index-level series.

    Uses date-based lookback (365 days) so it works correctly for both
    monthly series (e.g. PCE) and daily series (e.g. gold prices).
    """
    from datetime import timedelta
    series = _fetch_with_retry(series_id)
    if series.empty:
        raise ValueError(f"No data returned for {series_id}")
    latest_date = series.index[-1]
    one_year_ago = latest_date - timedelta(days=365)
    prior = series[series.index <= one_year_ago]
    if prior.empty:
        raise ValueError(f"Not enough history for YoY calculation: {series_id}")
    return float((series.iloc[-1] / prior.iloc[-1] - 1) * 100)


def load_all_series(series_map: dict[str, str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for label, series_id in series_map.items():
        try:
            if label in YOY_SERIES:
                results[label] = get_series_yoy(series_id)
            else:
                results[label] = get_series_latest(series_id)
        except Exception as exc:  # pragma: no cover - network/runtime variability
            results[label] = {"error": str(exc), "series_id": series_id}
    return results


def load_series_range(series_id: str, start: str, end: str) -> pd.Series:
    import socket
    last_exc: Exception | None = None
    for attempt in range(_MAX_TRIES):
        try:
            socket.setdefaulttimeout(_TIMEOUT)
            series = _get_client().get_series(
                series_id, observation_start=start, observation_end=end
            ).dropna()
            series.index = pd.to_datetime(series.index)
            return series
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_TRIES - 1:
                time.sleep(_RETRY_WAIT)
        finally:
            socket.setdefaulttimeout(None)
    raise RuntimeError(f"FRED range request failed after {_MAX_TRIES} attempts for {series_id}: {last_exc}")


def load_dataset(series_map: dict[str, str], start: str, end: str, freq: str = "M") -> pd.DataFrame:
    frame = pd.DataFrame()
    for label, series_id in series_map.items():
        try:
            frame[label] = load_series_range(series_id, start, end)
        except Exception:
            pass  # optional series missing — column simply absent from frame
    frame = frame.dropna(how="all").sort_index()
    if freq:
        frame = frame.resample(freq).last().dropna(how="all")
    # Apply YoY transformation for index-level series
    for label in YOY_SERIES:
        if label in frame.columns:
            frame[label] = frame[label].ffill().pct_change(12, fill_method=None) * 100
    return frame
