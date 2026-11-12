"""Tests for vintage coverage and failure transparency."""
from datetime import date

import pytest

from backtesting.point_in_time import HistoricalFeature, HistoricalSnapshot
from backtesting.vintage_runner import collect_vintage_runs, vintage_coverage


def fake_snapshot(origin, observation_start, *, series_map, api_key, session):
    if origin == date(2008, 2, 15):
        raise RuntimeError("FRED API unavailable")
    val = None if origin == date(2008, 1, 15) else 5.0
    return HistoricalSnapshot(
        forecast_origin=origin,
        features={
            "unemployment": HistoricalFeature(
                label="unemployment", series_id="UNRATE",
                vintage_date=origin,
                observation_date=date(2007, 12, 1) if val is not None else None,
                value=val, transformation="level",
                status="available" if val is not None else "no_observations",
            )
        },
    )


def test_all_origins_are_accounted_for():
    rows = collect_vintage_runs(
        ["2008-03-15", "2008-01-15", "2008-02-15"], "2007-01-01",
        series_map={"unemployment": "UNRATE"},
        snapshot_builder=fake_snapshot,
    )
    assert [row.status for row in rows] == ["incomplete", "error", "available"]
    assert rows[0].missing_features == ("unemployment",)
    assert "FRED API unavailable" in rows[1].error
    coverage = vintage_coverage(rows)
    assert coverage == {
        "total_origins": 3, "available": 1, "incomplete": 1,
        "errors": 1, "available_fraction": pytest.approx(1 / 3),
    }


def test_duplicate_origins_are_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        collect_vintage_runs(
            ["2008-01-15", "2008-01-15"], "2007-01-01",
            series_map={"unemployment": "UNRATE"},
            snapshot_builder=fake_snapshot,
        )


def test_unknown_required_features_are_rejected():
    with pytest.raises(ValueError, match="Required"):
        collect_vintage_runs(
            ["2008-01-15"], "2007-01-01",
            series_map={"unemployment": "UNRATE"},
            required_features=["inflation"],
            snapshot_builder=fake_snapshot,
        )


def test_empty_origin_coverage_is_well_defined():
    assert vintage_coverage([])["available_fraction"] == 0.0
