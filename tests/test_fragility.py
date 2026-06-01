from engine.fragility import score_fragility


def test_fragility_has_expected_fields():
    scores = score_fragility({"hy_spread": 6.2, "2y": 4.2, "10y": 3.7})
    assert scores["liquidity"] == 2
    assert "correlation" in scores


# --- Dynamic leverage ---

def test_leverage_zero_when_data_unavailable():
    scores = score_fragility({"hy_spread": 3.0, "2y": 3.5, "10y": 4.0})
    assert scores["leverage"] == 0


def test_leverage_moderate_above_threshold():
    scores = score_fragility({
        "hy_spread": 3.0, "2y": 3.5, "10y": 4.0,
        "debt_service": 11.0,  # above moderate (10.5), below high (12.0)
    })
    assert scores["leverage"] == 1


def test_leverage_high_above_crisis_threshold():
    scores = score_fragility({
        "hy_spread": 3.0, "2y": 3.5, "10y": 4.0,
        "debt_service": 12.5,  # above high (12.0)
    })
    assert scores["leverage"] == 2


def test_leverage_zero_in_deleveraged_environment():
    scores = score_fragility({
        "hy_spread": 3.0, "2y": 3.5, "10y": 4.0,
        "debt_service": 9.5,  # below moderate threshold
    })
    assert scores["leverage"] == 0
