"""Contract tests for point-in-time FRED data access; no live API key needed."""
from datetime import date

import pytest

from data.loaders.alfred_loader import (
    asof_series_to_pandas,
    fetch_asof_series,
    latest_asof_snapshot,
)


class FakeResponse:
    def __init__(self, observations, status_error=False):
        self._observations = observations
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise RuntimeError("HTTP failure")

    def json(self):
        return {"observations": self._observations}


class FakeSession:
    def __init__(self, observations):
        self.observations = observations
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.observations)


def item(observation_date, value, *, vintage="2008-01-15"):
    return {
        "date": observation_date,
        "value": value,
        "realtime_start": vintage,
        "realtime_end": vintage,
    }


def test_query_requests_historical_vintage_and_no_future_observations():
    session = FakeSession([item("2007-11-01", "4.7"), item("2007-12-01", "5.0")])
    observations = fetch_asof_series(
        "UNRATE", "2008-01-15", "2007-01-01", api_key="fake", session=session
    )
    assert [obs.value for obs in observations] == [4.7, 5.0]
    assert observations[-1].observation_date == date(2007, 12, 1)
    url, params, timeout = session.calls[0]
    assert params["realtime_start"] == "2008-01-15"
    assert params["realtime_end"] == "2008-01-15"
    assert params["observation_end"] == "2008-01-15"
    assert params["observation_start"] == "2007-01-01"
    assert timeout == 30


def test_missing_value_stays_missing_not_zero():
    session = FakeSession([item("2007-12-01", ".")])
    results = latest_asof_snapshot(
        {"unemployment": "UNRATE"}, "2008-01-15", "2007-01-01",
        api_key="fake", session=session,
    )
    assert results["unemployment"] is None


def test_future_observation_is_rejected():
    session = FakeSession([item("2008-02-01", "5.0")])
    with pytest.raises(ValueError, match="inconsistent"):
        fetch_asof_series(
            "UNRATE", "2008-01-15", "2007-01-01", api_key="fake", session=session
        )


def test_wrong_vintage_is_rejected():
    session = FakeSession([item("2007-12-01", "5.0", vintage="2009-01-15")])
    with pytest.raises(ValueError, match="inconsistent"):
        fetch_asof_series(
            "UNRATE", "2008-01-15", "2007-01-01", api_key="fake", session=session
        )


def test_mixed_vintages_not_concatenated_as_one_series():
    session_1 = FakeSession([item("2007-12-01", "5.0", vintage="2008-01-15")])
    session_2 = FakeSession([item("2007-11-01", "4.7", vintage="2008-02-15")])
    first = fetch_asof_series(
        "UNRATE", "2008-01-15", "2007-01-01", api_key="fake", session=session_1
    )
    second = fetch_asof_series(
        "UNRATE", "2008-02-15", "2007-01-01", api_key="fake", session=session_2
    )
    with pytest.raises(ValueError, match="different vintages"):
        asof_series_to_pandas(first + second)


def test_missing_key_and_inverted_dates_fail_closed():
    with pytest.raises(ValueError, match="observation_start"):
        fetch_asof_series("UNRATE", "2008-01-15", "2009-01-01", api_key="fake")
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        fetch_asof_series("UNRATE", "2008-01-15", "2007-01-01", api_key="")


def test_vintage_series_keeps_dates_and_values():
    session = FakeSession([item("2007-12-01", "5.0"), item("2007-11-01", "4.7")])
    data = fetch_asof_series(
        "UNRATE", "2008-01-15", "2007-01-01", api_key="fake", session=session
    )
    series = asof_series_to_pandas(data)
    assert list(series.values) == [4.7, 5.0]
    assert series.index[0].date() == date(2007, 11, 1)
