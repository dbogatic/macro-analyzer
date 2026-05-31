from config.base_weights import BASE_WEIGHTS
from engine.weighting import adjust_weights


def test_weighting_normalizes_to_one():
    weights, rationale = adjust_weights(
        BASE_WEIGHTS,
        {"policy": 2, "growth": 0, "financial": 2, "curve": 1},
        {"liquidity": 2},
        "Break",
    )
    assert round(sum(weights.values()), 6) == 1.0
    assert len(rationale) >= 1
