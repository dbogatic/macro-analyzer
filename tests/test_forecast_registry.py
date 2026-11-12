"""Offline SQLite registry contract tests (no market data or API keys)."""
from datetime import date, datetime, timezone
import sqlite3

import pytest

from data.storage.forecast_registry import Forecast, ForecastRegistry


def sample_forecast(forecast_id="test-1", prediction=0.25):
    return Forecast(
        forecast_id=forecast_id,
        issued_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        model_name="historical_base_rate",
        model_version="0.1",
        target_name="recession_onset_12m",
        target_definition="New recession starts in next 12 calendar months",
        window_start=date(2025, 1, 2),
        window_end=date(2025, 12, 31),
        kind="binary",
        prediction=prediction,
        features={"unemployment": {"value": 4.2, "vintage": "2025-01-01"}},
        source_manifest={"origin": "synthetic_test_data"},
    )


def test_forecasts_are_append_only(tmp_path):
    registry = ForecastRegistry(tmp_path / "forecasts.db")
    f = sample_forecast()
    registry.record_forecast(f)
    with pytest.raises(sqlite3.IntegrityError):
        registry.record_forecast(f)
    with registry._connect() as con:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            con.execute("UPDATE forecast_records SET prediction=0.7")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            con.execute("DELETE FROM forecast_records")
    assert registry.target_counts("recession_onset_12m")["total_forecasts"] == 1


def test_outcomes_revisions_and_expiry(tmp_path):
    registry = ForecastRegistry(tmp_path / "forecasts.db")
    registry.record_forecast(sample_forecast())
    with pytest.raises(ValueError, match="not ended"):
        registry.record_outcome(
            "test-1", 0, recorded_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            source_name="synthetic_label", source_version="v1",
        )
    for version, outcome in [("v1", 0), ("v2", 1)]:
        registry.record_outcome(
            "test-1", outcome,
            recorded_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            source_name="synthetic_label", source_version=version,
        )
    first = registry.scored_rows(
        target_name="recession_onset_12m",
        source_name="synthetic_label", source_version="v1",
    )
    second = registry.scored_rows(
        target_name="recession_onset_12m",
        source_name="synthetic_label", source_version="v2",
    )
    assert first[0]["outcome"] == 0
    assert second[0]["outcome"] == 1
    assert registry.target_counts("recession_onset_12m")["with_any_outcome"] == 1


def test_invalid_probability_and_timestamps(tmp_path):
    registry = ForecastRegistry(tmp_path / "forecasts.db")
    with pytest.raises(ValueError, match="between 0 and 1"):
        registry.record_forecast(sample_forecast(prediction=1.2))
    registry.record_forecast(sample_forecast())
    with pytest.raises(ValueError, match="timezone"):
        registry.record_outcome(
            "test-1", 0, recorded_at=datetime(2026, 1, 1),
            source_name="synthetic_label", source_version="v1",
        )


def test_reinitializing_preserves_forecasts(tmp_path):
    destination = tmp_path / "forecasts.db"
    registry = ForecastRegistry(destination)
    registry.record_forecast(sample_forecast())
    ForecastRegistry(destination).initialize()
    assert ForecastRegistry(destination).target_counts("recession_onset_12m")["total_forecasts"] == 1
