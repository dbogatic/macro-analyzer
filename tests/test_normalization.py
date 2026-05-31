from engine.normalization import finalize_scenarios


def test_finalized_scenarios_valid():
    scenarios, errors = finalize_scenarios([
        {"name": "Controlled Deceleration", "probability": (0.4, 0.5), "confidence": "Moderate"},
        {"name": "Stabilization / Policy Relief", "probability": (0.2, 0.3), "confidence": "Moderate"},
        {"name": "Downside Break", "probability": (0.2, 0.3), "confidence": "Low-Moderate"},
    ], 4)
    assert not errors
    assert len(scenarios) == 3
