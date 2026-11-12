"""Point-in-time FRED/ALFRED observations for research and historical forecasts.

See https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

Unlike the ordinary FRED loader, this module requests the vintage that was
available on a specified historical date. It does NOT silently substitute
today's revised values if ALFRED returns no observations.

Limitations: date-level vintages do not establish intraday availability.
The calling forecast scheduler must use a defensible cutoff AFTER releases.
Series outside ALFRED coverage must be treated as unavailable, not backfilled
with final values.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Mapping

import pandas as pd
import requests

from config.settings import settings

_ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"


@dataclass(frozen=True)
class AsOfObservation:
    series_id: str
    as_of_date: date
    observation_date: date
    value: float
    realtime_start: date
    realtime_end: date


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def fetch_asof_series(
    series_id: str,
    as_of_date: str | date,
    observation_start: str | date,
    *,
    api_key: str | None = None,
    session: requests.Session | None = None,
) -> list[AsOfObservation]:
    """Return observations actually known on the requested historical date.

    Missing '.' values are excluded; the caller decides whether the remaining
    data are sufficient. An HTTP/API failure raises rather than using final
    revised data. Inputs specify calendar dates, not times of day.
    """
    asof = _parse_date(as_of_date)
    start = _parse_date(observation_start)
    if start > asof:
        raise ValueError("observation_start cannot be later than as_of_date")
    key = api_key or settings.fred_api_key
    if not key:
        raise RuntimeError("FRED_API_KEY is required for vintage requests")

    requester = session if session is not None else requests
    response = requester.get(
        _ENDPOINT,
        params={
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "realtime_start": asof.isoformat(),
            "realtime_end": asof.isoformat(),
            "observation_start": start.isoformat(),
            "observation_end": asof.isoformat(),
            "limit": 100000,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "error_code" in payload:
        raise RuntimeError(f"FRED vintage request failed: {payload.get('error_message', 'unknown error')}")
    if "observations" not in payload:
        raise ValueError("FRED vintage response has no observations field")

    observations: list[AsOfObservation] = []
    for raw in payload["observations"]:
        value = raw.get("value")
        if value in (None, ".", ""):
            continue
        numeric = float(value)
        if not isfinite(numeric):
            continue
        observed = _parse_date(raw["date"])
        valid_from = _parse_date(raw["realtime_start"])
        valid_to = _parse_date(raw["realtime_end"])
        if observed > asof or not (valid_from <= asof <= valid_to):
            raise ValueError(
                f"FRED returned an observation inconsistent with requested vintage: {series_id}"
            )
        observations.append(AsOfObservation(
            series_id=series_id,
            as_of_date=asof,
            observation_date=observed,
            value=numeric,
            realtime_start=valid_from,
            realtime_end=valid_to,
        ))
    return sorted(observations, key=lambda item: item.observation_date)


def latest_asof_snapshot(
    series_map: Mapping[str, str],
    as_of_date: str | date,
    observation_start: str | date,
    *,
    api_key: str | None = None,
    session: requests.Session | None = None,
) -> dict[str, AsOfObservation | None]:
    """Return latest available vintage observation WITH its observation date.

    This does not convert index levels to annual changes. Such transformations
    must use only earlier observations from the *same* vintage.
    """
    results: dict[str, AsOfObservation | None] = {}
    for label, series_id in series_map.items():
        observations = fetch_asof_series(
            series_id, as_of_date, observation_start,
            api_key=api_key, session=session,
        )
        results[label] = observations[-1] if observations else None
    return results


def asof_series_to_pandas(observations: list[AsOfObservation]) -> pd.Series:
    """Convert one as-of vintage into a dated series; no implicit filling."""
    if not observations:
        return pd.Series(dtype=float)
    if len({o.as_of_date for o in observations}) != 1:
        raise ValueError("Cannot combine different vintages as one historical series")
    if len({o.series_id for o in observations}) != 1:
        raise ValueError("Cannot combine different FRED series")
    return pd.Series(
        [item.value for item in observations],
        index=pd.DatetimeIndex([item.observation_date for item in observations]),
        dtype=float,
        name=observations[0].series_id,
    ).sort_index()
