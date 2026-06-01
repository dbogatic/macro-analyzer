from __future__ import annotations


def classify_momentum(
    current_unemployment: float,
    previous_unemployment: float | None,
    unemployment_3m_trend: str | None = None,
    jobless_claims_yoy: float | None = None,
) -> str:
    """Classify labor market momentum as Deteriorating, Improving, or Stable.

    Single-month unemployment change is noisy. The composite logic requires
    corroboration before overriding a Stable reading: the 3-month trend and
    jobless claims YoY must agree with the single-month signal to flip the
    classification. When only one signal is available the single-month
    comparison is used as the fallback (preserving original behavior).

    Args:
        current_unemployment:  Latest unemployment rate.
        previous_unemployment: Prior month's unemployment rate (or None on first run).
        unemployment_3m_trend: "Rising" / "Falling" / "Stable" over 3 months.
        jobless_claims_yoy:    YoY % change in initial jobless claims (ICSA).
                               Positive = more claims = worsening.
    """
    if previous_unemployment is None:
        return "Stable"

    single_month = (
        "Deteriorating" if current_unemployment > previous_unemployment else
        "Improving"     if current_unemployment < previous_unemployment else
        "Stable"
    )

    # No extra signals — fall back to original single-month behavior
    if unemployment_3m_trend is None and jobless_claims_yoy is None:
        return single_month

    # Build corroboration count for each direction
    deteriorating_signals = 0
    improving_signals     = 0

    if single_month == "Deteriorating":
        deteriorating_signals += 1
    elif single_month == "Improving":
        improving_signals += 1

    if unemployment_3m_trend == "Rising":
        deteriorating_signals += 1
    elif unemployment_3m_trend == "Falling":
        improving_signals += 1

    if jobless_claims_yoy is not None:
        if jobless_claims_yoy > 5.0:     # claims rising meaningfully YoY
            deteriorating_signals += 1
        elif jobless_claims_yoy < -5.0:  # claims falling meaningfully YoY
            improving_signals += 1

    # Override Stable only when at least 2 signals agree on a direction
    if deteriorating_signals >= 2:
        return "Deteriorating"
    if improving_signals >= 2:
        return "Improving"
    return "Stable"
