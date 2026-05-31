from engine.auto_scoring import build_constraint_scores


def test_constraint_scores_keys():
    scores = build_constraint_scores({
        "core_pce": 3.1,
        "unemployment": 4.2,
        "hy_spread": 4.5,
        "2y": 4.0,
        "10y": 3.8,
    })
    assert set(scores.keys()) == {"policy", "growth", "financial", "curve"}
