from engine.momentum import classify_momentum


def test_single_month_deteriorating_without_extra_signals():
    assert classify_momentum(4.5, 4.3) == "Deteriorating"


def test_single_month_improving_without_extra_signals():
    assert classify_momentum(4.0, 4.3) == "Improving"


def test_stable_without_extra_signals():
    assert classify_momentum(4.3, 4.3) == "Stable"


def test_no_previous_returns_stable():
    assert classify_momentum(4.5, None) == "Stable"


def test_composite_requires_two_signals_to_override_stable():
    # Single-month stable + only 3m trend rising — not enough to flip
    result = classify_momentum(4.3, 4.3, unemployment_3m_trend="Rising")
    assert result == "Stable"


def test_composite_two_deteriorating_signals_override():
    # Single-month up + 3m trend Rising → Deteriorating
    result = classify_momentum(4.5, 4.3, unemployment_3m_trend="Rising")
    assert result == "Deteriorating"


def test_composite_jobless_claims_corroborates_deteriorating():
    # Single-month up + claims rising YoY → Deteriorating
    result = classify_momentum(4.5, 4.3, jobless_claims_yoy=8.0)
    assert result == "Deteriorating"


def test_composite_improving_with_two_signals():
    result = classify_momentum(4.0, 4.3, unemployment_3m_trend="Falling")
    assert result == "Improving"


def test_composite_conflicting_signals_return_stable():
    # Single-month up but claims falling — conflict → Stable
    result = classify_momentum(4.5, 4.3, jobless_claims_yoy=-8.0)
    assert result == "Stable"
