"""Chronological point-in-time snapshot collection.

This runner is intentionally separate from the legacy descriptive backtest.
It NEVER substitutes revised observations for missing ALFRED vintages and
NEVER discards an unsuccessful origin from its accounting.

A collected snapshot is not a fitted model or recession probability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable, Mapping

from backtesting.point_in_time import HistoricalSnapshot, build_historical_snapshot


@dataclass(frozen=True)
class VintageRun:
    origin: date
    status: str
    missing_features: tuple[str, ...]
    snapshot: HistoricalSnapshot | None
    error: str | None = None


def collect_vintage_runs(
    origins: Iterable[date | str],
    observation_start: date | str,
    *,
    series_map: Mapping[str, str],
    required_features: Iterable[str] | None = None,
    snapshot_builder: Callable[..., HistoricalSnapshot] = build_historical_snapshot,
    api_key: str | None = None,
    session=None,
) -> list[VintageRun]:
    """Collect one as-of vintage at each predetermined forecast origin.

    Caller controls the historical schedule and end-of-day availability rule.
    A network/API error is an explicit failed run. Missing indicators produce
    incomplete runs; neither type is dropped. Default: all mapped series
    are required, but callers can choose a model-specific subset.
    """
    required = set(series_map) if required_features is None else set(required_features)
    unknown = required.difference(series_map)
    if unknown:
        raise ValueError(f"Required features not in series_map: {sorted(unknown)}")

    results: list[VintageRun] = []
    dates = [value if isinstance(value, date) else date.fromisoformat(value)
             for value in origins]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicate forecast origins")
    for origin in sorted(dates):
        try:
            snapshot = snapshot_builder(
                origin, observation_start,
                series_map=series_map, api_key=api_key, session=session,
            )
            missing = tuple(sorted(required.intersection(snapshot.incomplete)))
            results.append(VintageRun(
                origin=origin,
                status="incomplete" if missing else "available",
                missing_features=missing,
                snapshot=snapshot,
            ))
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            results.append(VintageRun(
                origin=origin, status="error", missing_features=(),
                snapshot=None, error=f"{type(exc).__name__}: {exc}",
            ))
    return results


def vintage_coverage(runs: Iterable[VintageRun]) -> dict[str, int | float]:
    """Count all forecast origins, including unavailable and failed periods."""
    rows = list(runs)
    available = sum(r.status == "available" for r in rows)
    incomplete = sum(r.status == "incomplete" for r in rows)
    errors = sum(r.status == "error" for r in rows)
    total = len(rows)
    return {
        "total_origins": total,
        "available": available,
        "incomplete": incomplete,
        "errors": errors,
        "available_fraction": available / total if total else 0.0,
    }
