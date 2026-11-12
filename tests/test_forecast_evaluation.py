"""Pure scoring tests with synthetic outcomes."""
import pytest

from data.storage.forecast_evaluation import evaluate_binary, evaluate_continuous


def test_binary_scores_and_missing_sample():
    score = evaluate_binary([
        {"prediction": 0.25, "outcome": 0},
        {"prediction": 0.75, "outcome": 1},
    ])
    assert score["n"] == 2
    assert score["brier"] == pytest.approx(0.0625)
    assert score["log_loss"] > 0
    assert evaluate_binary([])["brier"] is None


def test_invalid_probability_rejected():
    with pytest.raises(ValueError, match="Binary"):
        evaluate_binary([{"prediction": 1.2, "outcome": 0}])


def test_continuous_errors_and_interval_coverage():
    result = evaluate_continuous([
        {"prediction": 2.0, "outcome": 3.0, "lower": 1.0, "upper": 4.0},
        {"prediction": 4.0, "outcome": 6.0, "lower": 3.0, "upper": 5.0},
    ])
    assert result["mae"] == pytest.approx(1.5)
    assert result["rmse"] == pytest.approx((2.5)**0.5)
    assert result["interval_n"] == 2
    assert result["interval_coverage"] == pytest.approx(0.5)


def test_incomplete_interval_rejected():
    with pytest.raises(ValueError, match="Incomplete"):
        evaluate_continuous([
            {"prediction": 2, "outcome": 3, "lower": 1, "upper": None}
        ])
