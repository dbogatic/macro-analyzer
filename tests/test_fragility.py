import math

import pytest

from engine.fragility import missing_fragility_components, score_fragility


def baseline(**overrides):
    return {
        "hy_spread": 3.0, "2y": 3.5, "10y": 4.0,
        "vix": 18.0, "oil": 65.0, "gold": 0.0,
        "debt_service": 9.5, **overrides,
    }


def test_complete_fragility_has_four_scored_dimensions():
    scores = score_fragility(baseline())
    assert set(scores) == {"leverage", "liquidity", "energy_dependency", "institutional"}
    assert missing_fragility_components(scores) == []
    assert sum(scores.values()) == 0


def test_term_spread_does_not_change_fragility():
    inverted = score_fragility(baseline(**{"2y": 5.0, "10y": 3.0}))
    normal = score_fragility(baseline(**{"2y": 3.0, "10y": 5.0}))
    assert inverted == normal
    assert "correlation" not in inverted


@pytest.mark.parametrize("key", ["debt_service", "vix", "oil", "gold"])
def test_missing_optional_inputs_are_not_zero(key):
    values = baseline()
    values.pop(key)
    scores = score_fragility(values)
    assert missing_fragility_components(scores)
    assert None in scores.values()


def test_nan_is_missing_not_benign():
    assert score_fragility(baseline(oil=math.nan))["energy_dependency"] is None


def test_observed_leverage_thresholds():
    assert score_fragility(baseline(debt_service=9.5))["leverage"] == 0
    assert score_fragility(baseline(debt_service=11.0))["leverage"] == 1
    assert score_fragility(baseline(debt_service=12.5))["leverage"] == 2
    assert score_fragility(baseline(debt_service=None))["leverage"] is None


def test_credit_spread_stress_affects_liquidity():
    assert score_fragility(baseline(hy_spread=6.2))["liquidity"] == 2
