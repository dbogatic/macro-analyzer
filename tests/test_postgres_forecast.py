"""Offline PostgreSQL contract checks; no live credentials required."""
from datetime import date, datetime, timezone

import pytest

from data.storage.postgres_forecast import PostgresForecastRegistry, SCHEMA
from data.storage.forecast_registry import Forecast


def fake_forecast(prediction=0.25):
    return Forecast(
        forecast_id="synthetic-1",
        issued_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        model_name="baseline", model_version="0.1",
        target_name="recession_onset_12m",
        target_definition="Synthetic 12-month recession indicator",
        window_start=date(2025, 1, 2),
        window_end=date(2025, 12, 31),
        kind="binary", prediction=prediction,
        features={"data": "synthetic"}, source_manifest={"source": "test"},
    )


class FakeConnection:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, kind, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        return self


def test_schema_has_immutable_records_and_versioned_outcomes():
    assert "CREATE TABLE IF NOT EXISTS forecast_records" in SCHEMA
    assert "CREATE TABLE IF NOT EXISTS forecast_outcomes" in SCHEMA
    assert "UNIQUE(forecast_id, source_name, source_version)" in SCHEMA
    assert "BEFORE UPDATE OR DELETE" in SCHEMA
    assert "REFERENCES forecast_records(forecast_id)" in SCHEMA


def test_insert_uses_parameters_and_preserves_vintage_payload():
    obj = PostgresForecastRegistry.__new__(PostgresForecastRegistry)
    fake = FakeConnection()
    obj._connect = lambda: fake
    obj.record_forecast(fake_forecast())
    assert len(fake.executed) == 1
    statement, params = fake.executed[0]
    assert statement.count("%s") == 14
    assert params[0] == "synthetic-1"
    assert params[9] == 0.25
    assert "synthetic" in params[-2]


def test_invalid_probability_not_written():
    obj = PostgresForecastRegistry.__new__(PostgresForecastRegistry)
    fake = FakeConnection()
    obj._connect = lambda: fake
    with pytest.raises(ValueError, match="between 0 and 1"):
        obj.record_forecast(fake_forecast(prediction=1.5))
    assert not fake.executed
