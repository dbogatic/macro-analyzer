"""Read-only dashboard query tests against an actual temporary SQLite DB."""
from datetime import date, datetime, timezone

import pytest

from data.storage.forecast_queries import (
    list_forecast_history, list_models, list_outcome_revisions, list_targets,
)
from data.storage.forecast_registry import Forecast, ForecastRegistry
from data.storage.forecast_evaluation import evaluate_binary


def forecast(forecast_id, probability):
    return Forecast(
        forecast_id=forecast_id,
        issued_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        model_name="baseline", model_version="0.1",
        target_name="recession_onset_12m",
        target_definition="Recession onset in the specified 12-month window",
        window_start=date(2025, 1, 2),
        window_end=date(2025, 12, 31),
        kind="binary", prediction=probability,
        features={"source": "synthetic"},
        source_manifest={"source": "synthetic"},
    )


def test_empty_database_shows_no_targets(tmp_path):
    path = tmp_path / "forecasts.db"
    ForecastRegistry(path)
    assert list_targets(path) == []


def test_history_retains_forecasts_with_missing_outcomes(tmp_path):
    path = tmp_path / "forecasts.db"
    registry = ForecastRegistry(path)
    registry.record_forecast(forecast("a", 0.25))
    registry.record_forecast(forecast("b", 0.75))
    registry.record_outcome(
        "a", 0, recorded_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        source_name="NBER", source_version="v1",
    )
    assert list_targets(path) == ["recession_onset_12m"]
    assert list_models(path, "recession_onset_12m") == [("baseline", "0.1")]
    assert list_outcome_revisions(
        path, "recession_onset_12m", "baseline", "0.1"
    ) == [("NBER", "v1")]
    rows = list_forecast_history(
        path, "recession_onset_12m", "baseline", "0.1",
        source_name="NBER", source_version="v1",
    )
    assert len(rows) == 2
    assert [row["outcome"] for row in rows] == [0, None]
    assert rows[1]["prediction"] == pytest.approx(0.75)
    evaluated = [row for row in rows if row["outcome"] is not None]
    assert evaluate_binary(evaluated)["brier"] == pytest.approx(0.0625)


def test_unselected_revision_does_not_count_as_known_outcome(tmp_path):
    path = tmp_path / "forecasts.db"
    registry = ForecastRegistry(path)
    registry.record_forecast(forecast("a", 0.25))
    registry.record_outcome(
        "a", 0, recorded_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        source_name="NBER", source_version="v1",
    )
    rows = list_forecast_history(
        path, "recession_onset_12m", "baseline", "0.1",
        source_name="NBER", source_version="v2",
    )
    assert len(rows) == 1
    assert rows[0]["outcome"] is None


def test_partial_revision_selection_rejected(tmp_path):
    path = tmp_path / "forecasts.db"
    ForecastRegistry(path)
    with pytest.raises(ValueError, match="selected together"):
        list_forecast_history(
            path, "recession_onset_12m", "baseline", "0.1",
            source_name="NBER",
        )
