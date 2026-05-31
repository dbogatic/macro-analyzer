from engine.scenarios import build_scenarios


def test_scenarios_three_paths():
    scenarios = build_scenarios({
        "constraint_score": 5,
        "fragility_score": 4,
        "momentum": "Stable",
        "regime": "Stress",
    })
    assert len(scenarios) == 3
