from __future__ import annotations

import time
from typing import Any

import pandas as pd
from fredapi import Fred

from config.settings import settings

# Series that return index levels and must be converted to YoY % change
YOY_SERIES = {"core_pce", "cpi", "gold", "jobless_claims"}

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


def get_unemployment_3m_trend(series_id: str = "UNRATE", months: int = 3) -> str:
    """Return unemployment trend direction over the last N months.

    Returns "Rising", "Falling", or "Stable". Used to smooth the single-month
    momentum signal which is noisy on monthly FRED data.
    """
    series = _fetch_with_retry(series_id).dropna()
    monthly = series.resample("ME").last().dropna()
    if len(monthly) < months + 1:
        return "Stable"
    delta = float(monthly.iloc[-1] - monthly.iloc[-(months + 1)])
    if delta > 0.1:
        return "Rising"
    if delta < -0.1:
        return "Falling"
    return "Stable"


def get_series_delta(series_id: str, months: int = 3) -> float:
    """Return the change in a series over the last N months (current minus N months ago).

    Positive = rising, negative = falling. Used to compute trend direction for
    HY spread and yield curve without requiring a full historical dataset load.
    """
    series = _fetch_with_retry(series_id)
    series = series.dropna()
    if len(series) < months + 1:
        raise ValueError(f"Not enough history for {months}-month delta: {series_id}")
    monthly = series.resample("ME").last().dropna()
    if len(monthly) < months + 1:
        raise ValueError(f"Not enough monthly observations for delta: {series_id}")
    return float(monthly.iloc[-1] - monthly.iloc[-(months + 1)])


def load_financial_trend(
    hy_series_id: str = "BAMLH0A0HYM2",
    y2_series_id: str = "DGS2",
    y10_series_id: str = "DGS10",
    months: int = 3,
    hy_threshold: float = 0.5,
    curve_threshold: float = 0.2,
) -> dict[str, str | float | None]:
    """Return trend labels for HY spread and yield curve over the last N months.

    Labels: "Widening" / "Tightening" / "Stable" for HY spread.
            "Inverting" / "Normalizing" / "Stable" for yield curve.
    Returns None values and an error key if data cannot be loaded.
    """
    try:
        hy_delta = get_series_delta(hy_series_id, months)
        hy_trend = (
            "Widening"   if hy_delta >  hy_threshold else
            "Tightening" if hy_delta < -hy_threshold else
            "Stable"
        )
    except Exception as exc:
        return {"hy_trend": None, "curve_trend": None, "error": str(exc)}

    try:
        y2_delta  = get_series_delta(y2_series_id,  months)
        y10_delta = get_series_delta(y10_series_id, months)
        curve_delta = (y10_delta - y2_delta)
        curve_trend = (
            "Normalizing" if curve_delta >  curve_threshold else
            "Inverting"   if curve_delta < -curve_threshold else
            "Stable"
        )
    except Exception as exc:
        return {"hy_trend": hy_trend, "curve_trend": None, "error": str(exc)}

    return {
        "hy_trend":    hy_trend,
        "curve_trend": curve_trend,
        "hy_delta":    round(hy_delta, 3),
        "curve_delta": round(curve_delta, 3),
    }


def load_dataset(series_map: dict[str, str], start: str, end: str, freq: str = "ME") -> pd.DataFrame:
    # Resample each series to the target frequency INDIVIDUALLY before joining.
    # This prevents index misalignment between monthly series (first-of-month
    # dates from FRED) and daily series (trading-day dates) which would cause
    # daily series to be all-NaN after alignment to a monthly frame index.
    columns: dict[str, pd.Series] = {}
    for label, series_id in series_map.items():
        try:
            s = load_series_range(series_id, start, end)
            if freq:
                s = s.resample(freq).last()
            columns[label] = s
        except Exception:
            pass  # optional series missing — column simply absent from frame

    if not columns:
        return pd.DataFrame()

    frame = pd.DataFrame(columns).sort_index().dropna(how="all")

    # Apply YoY transformation for index-level series
    for label in YOY_SERIES:
        if label in frame.columns:
            frame[label] = frame[label].ffill().pct_change(12) * 100
    return frame
