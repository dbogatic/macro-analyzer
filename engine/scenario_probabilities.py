from __future__ import annotations


def assign_probabilities(constraint_score: float, fragility_score: float, momentum: str) -> dict[str, tuple[float, float]]:
    """
    Assign scenario probabilities based on constraint score, fragility score, and momentum.

    Starting point: 45% base / 30% upside / 25% downside reflects a
    late-cycle economy with moderate constraints — not a neutral baseline.
    Graduated thresholds (3/5/7 out of 10) ensure the distribution responds
    to moderate stress, not just crisis-level readings.
    """
    base = 0.45
    upside = 0.30
    downside = 0.25

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
