"""Offline unit tests for point-in-time feature engineering."""
from datetime import date

import pytest

from backtesting.point_in_time import build_historical_snapshot, snapshot_for_research


def raw(obs_date, value, *, vintage="2008-01-15"):
    return {
        "date": obs_date, "value": str(value),
        "realtime_start": vintage, "realtime_end": vintage,
    }


class Response:
    def __init__(self, observations):
        self._observations = observations

    def raise_for_status(self):
        pass

    def json(self):
        return {"observations": self._observations}


class MockSession:
    def __init__(self, by_series):
        self.by_series = by_series
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append(params.copy())
        return Response(self.by_series[params["series_id"]])


def test_snapshot_uses_exact_same_month_one_year_prior():
    session = MockSession({
        "CPIAUCSL": [
            raw("2006-12-01", 100),
            raw("2007-01-01", 150),
            raw("2007-12-01", 104),
        ]
    })
    snapshot = build_historical_snapshot(
        "2008-01-15", "2006-01-01",
        series_map={"cpi": "CPIAUCSL"}, api_key="fake", session=session,
    )
    # December to December = +4%, NOT a positional 12-row change.
    assert snapshot.features["cpi"].value == pytest.approx(4.0)
    assert snapshot.features["cpi"].observation_date == date(2007, 12, 1)
    assert snapshot.incomplete == []
    assert session.calls[0]["realtime_start"] == "2008-01-15"


def test_snapshot_reports_missing_year_ago_month():
    session = MockSession({
        "CPIAUCSL": [raw("2007-01-01", 100), raw("2007-12-01", 104)]
    })
    snapshot = build_historical_snapshot(
        "2008-01-15", "2007-01-01",
        series_map={"cpi": "CPIAUCSL"}, api_key="fake", session=session,
    )
    assert snapshot.incomplete == ["cpi"]
    assert snapshot.features["cpi"].status == "missing_year_ago_month"


def test_snapshot_preserves_missing_component_and_provenance():
    session = MockSession({"UNRATE": [raw("2007-12-01", 5.0)], "VIXCLS": []})
    snapshot = build_historical_snapshot(
        "2008-01-15", "2007-01-01",
        series_map={"unemployment": "UNRATE", "vix": "VIXCLS"},
        api_key="fake", session=session,
    )
    output = snapshot_for_research(snapshot)
    assert output["features"]["unemployment"]["value"] == 5.0
    assert output["features"]["unemployment"]["observation_date"] == "2007-12-01"
    assert output["features"]["unemployment"]["vintage_date"] == "2008-01-15"
    assert output["features"]["vix"]["value"] is None
    assert output["incomplete"] == ["vix"]


def test_weekly_claims_are_not_processed_as_monthly_yoy():
    session = MockSession({"ICSA": [raw("2008-01-05", 350_000)]})
    snap = build_historical_snapshot(
        "2008-01-15", "2008-01-01",
        series_map={"jobless_claims": "ICSA"}, api_key="fake", session=session,
    )
    assert snap.features["jobless_claims"].value == 350_000
    assert snap.features["jobless_claims"].transformation == "level"


def test_no_future_vintage_fallback():
    session = MockSession({"UNRATE": [raw("2008-02-01", 5.0)]})
    with pytest.raises(ValueError, match="inconsistent"):
        build_historical_snapshot(
            "2008-01-15", "2007-01-01",
            series_map={"unemployment": "UNRATE"},
            api_key="fake", session=session,
        )


def test_no_cross_month_substitution_for_yoy():
    session = MockSession({"CPIAUCSL": [
        raw("2006-11-01", 100), raw("2007-12-01", 110)
    ]})
    snap = build_historical_snapshot(
        "2008-01-15", "2006-01-01",
        series_map={"cpi": "CPIAUCSL"}, api_key="fake", session=session,
    )
    assert snap.features["cpi"].value is None
    assert snap.features["cpi"].status == "missing_year_ago_month"
