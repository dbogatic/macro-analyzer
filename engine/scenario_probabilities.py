from __future__ import annotations

# Regime-conditional starting priors.
# Stabilization: system is clean — upside has real room.
# Stress: default late-cycle posture.
# Break: one or more scores >= 7; downside dominates before any score adjustments.
_REGIME_PRIORS: dict[str, dict[str, float]] = {
    "Stabilization": {"base": 0.50, "upside": 0.35, "downside": 0.15},
    "Stress":        {"base": 0.45, "upside": 0.30, "downside": 0.25},
    "Break":         {"base": 0.30, "upside": 0.20, "downside": 0.50},
}


def assign_probabilities(
    constraint_score: float,
    fragility_score: float,
    momentum: str,
    regime: str = "Stress",
    constraint_scores: dict | None = None,
    financial_trend: dict | None = None,
) -> dict[str, tuple[float, float]]:
    """
    Assign scenario probabilities from regime-conditional priors, graduated
    score adjustments, interaction terms, trend signals, and momentum.

    Starting priors are regime-conditional (see _REGIME_PRIORS). Score
    adjustments are graduated (3/5/7 thresholds). Interaction terms fire when
    two modules are co-stressed. Financial trend signals capture direction
    (widening vs tightening) which level-only scores miss near thresholds.
    """
    priors = _REGIME_PRIORS.get(regime, _REGIME_PRIORS["Stress"])
    base     = priors["base"]
    upside   = priors["upside"]
    downside = priors["downside"]

    # Constraint-driven shifts (graduated: mild / moderate / severe)
    if constraint_score >= 7:
        downside += 0.12
        base    -= 0.07
        upside  -= 0.05
    elif constraint_score >= 5:
        downside += 0.07
        base    -= 0.05
        upside  -= 0.02
    elif constraint_score >= 3:
        downside += 0.03
        base    -= 0.03

    # Fragility-driven shifts (graduated: mild / moderate / severe)
    if fragility_score >= 7:
        downside += 0.10
        base    -= 0.05
        upside  -= 0.05
    elif fragility_score >= 5:
        downside += 0.05
        base    -= 0.03
        upside  -= 0.02
    elif fragility_score >= 3:
        downside += 0.03
        base    -= 0.03

    # Cross-module interaction terms.
    # Two modules stressed simultaneously is qualitatively more dangerous than
    # the sum of their individual scores — these capture the feedback loops
    # (trapped Fed + credit stress, labor deterioration + credit widening)
    # that additive scoring misses.
    if constraint_scores:
        policy_stress    = constraint_scores.get("policy", 0) >= 1
        financial_stress = constraint_scores.get("financial", 0) >= 1
        growth_stress    = constraint_scores.get("growth", 0) >= 1

        if policy_stress and financial_stress:   # trapped Fed + credit stress
            downside += 0.03
            base     -= 0.02
            upside   -= 0.01

        if growth_stress and financial_stress:   # recession confirmation pattern
            downside += 0.02
            base     -= 0.02

    # Financial trend signals: direction matters near thresholds.
    # Same level while widening vs tightening represents different trajectories.
    if financial_trend:
        hy_trend    = financial_trend.get("hy_trend")
        curve_trend = financial_trend.get("curve_trend")

        if hy_trend == "Widening":
            downside += 0.02
            base     -= 0.01
            upside   -= 0.01
        elif hy_trend == "Tightening":
            upside   += 0.02
            base     -= 0.01
            downside -= 0.01

        if curve_trend == "Inverting":
            downside += 0.02
            base     -= 0.01
            upside   -= 0.01
        elif curve_trend == "Normalizing":
            upside   += 0.02
            base     -= 0.01
            downside -= 0.01

    # Momentum-driven shifts
    if momentum == "Deteriorating":
        downside += 0.05
        base    -= 0.05
    elif momentum == "Improving":
        upside += 0.05
        base   -= 0.05

    # Normalize so probabilities always sum to 1
    total    = base + upside + downside
    base    /= total
    upside  /= total
    downside /= total

    return {
        "base":     (round(base     - 0.05, 3), round(base     + 0.05, 3)),
        "upside":   (round(upside   - 0.05, 3), round(upside   + 0.05, 3)),
        "downside": (round(downside - 0.05, 3), round(downside + 0.05, 3)),
    }
