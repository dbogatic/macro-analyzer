from engine.fragility import score_fragility


def test_fragility_has_expected_fields():
    scores = score_fragility({"hy_spread": 6.2, "2y": 4.2, "10y": 3.7})
    assert scores["liquidity"] == 2
    assert "correlation" in scores
