"""Point-in-time research snapshots; separate from the legacy descriptive backtest.

Only observations from one ALFRED vintage may enter a snapshot. A monthly
YoY rate compares the same calendar month in consecutive years; it never
uses a positional pct_change(12) across gaps or unreleased observations.

No scenario probabilities are generated here. This module is not a validated
forecasting engine; it creates auditable inputs for one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

import pandas as pd

from config.fred_series import FRED_SERIES, MARKET_SIGNALS
from data.loaders.alfred_loader import AsOfObservation, fetch_asof_series

# Monthly price indexes needing exact-month YoY conversion. Weekly claims remain\n# an observed LEVEL until a separate weekly frequency-aware method is added.
_INDEX_YOY = frozenset({"core_pce", "cpi"})


@dataclass(frozen=True)
class HistoricalFeature:
    label: str
    series_id: str
    vintage_date: date
    observation_date: date | None
    value: float | None
    transformation: str
    status: str


@dataclass(frozen=True)
class HistoricalSnapshot:
    forecast_origin: date
    features: dict[str, HistoricalFeature]

    @property
    def incomplete(self) -> list[str]:
        return [name for name, item in self.features.items() if item.value is None]


def _latest(observations: list[AsOfObservation]) -> AsOfObservation | None:
    return observations[-1] if observations else None


def _monthly_yoy(observations: list[AsOfObservation]) -> tuple[float | None, str]:
    """Exact calendar-month pairing, using only the requested as-of vintage."""
    if not observations:
        return None, "no_observations"
    latest = observations[-1]
    month = pd.Period(latest.observation_date, freq="M")
    prior_month = month - 12
    lookup = {pd.Period(item.observation_date, freq="M"): item for item in observations}
    # Multiple dated observations in a month make a monthly index ambiguous.
    if len(lookup) != len(observations):
        return None, "non_monthly_or_duplicate_month"
    prior = lookup.get(prior_month)
    if prior is None:
        return None, "missing_year_ago_month"
    if prior.value <= 0:
        return None, "nonpositive_base"
    return 100.0 * (latest.value / prior.value - 1.0), "available"


def build_historical_snapshot(
    forecast_origin: str | date,
    observation_start: str | date,
    *,
    series_map: Mapping[str, str] | None = None,
    api_key: str | None = None,
    session=None,
) -> HistoricalSnapshot:
    """Read only the vintage available at the forecast origin (calendar day).

    A forecast recorded before all daily releases are completed must use an
    earlier cutoff. For scheduled historical evaluation, the caller must
    explicitly define end-of-day timing and source coverage.

    Missing values remain missing, with a reason. An API failure raises.
    """
    origin = (forecast_origin if isinstance(forecast_origin, date)
              else date.fromisoformat(forecast_origin))
    start = (observation_start if isinstance(observation_start, date)
             else date.fromisoformat(observation_start))
    if start > origin:
        raise ValueError("Observation history begins after forecast origin")
    if series_map is None:
        series_map = {**FRED_SERIES, **MARKET_SIGNALS}

    features: dict[str, HistoricalFeature] = {}
    for label, series_id in series_map.items():
        observations = fetch_asof_series(
            series_id, origin, start, api_key=api_key, session=session
        )
        latest = _latest(observations)
        transform = "year_over_year_percent" if label in _INDEX_YOY else "level"
        if transform == "year_over_year_percent":
            value, status = _monthly_yoy(observations)
        else:
            value = latest.value if latest is not None else None
            status = "available" if latest is not None else "no_observations"
        features[label] = HistoricalFeature(
            label=label,
            series_id=series_id,
            vintage_date=origin,
            observation_date=latest.observation_date if latest else None,
            value=value,
            transformation=transform,
            status=status,
        )
    return HistoricalSnapshot(forecast_origin=origin, features=features)


def snapshot_for_research(snapshot: HistoricalSnapshot) -> dict:
    """Serializable, provenance-rich snapshot; never imputes values."""
    return {
        "forecast_origin": snapshot.forecast_origin.isoformat(),
        "features": {
            name: {
                "series_id": item.series_id,
                "vintage_date": item.vintage_date.isoformat(),
                "observation_date": (
                    item.observation_date.isoformat() if item.observation_date else None
                ),
                "value": item.value,
                "transformation": item.transformation,
                "status": item.status,
            }
            for name, item in snapshot.features.items()
        },
        "incomplete": snapshot.incomplete,
    }
