from __future__ import annotations


def classify_momentum(current_unemployment: float, previous_unemployment: float | None) -> str:
    if previous_unemployment is None:
        return "Stable"
    if current_unemployment > previous_unemployment:
        return "Deteriorating"
    if current_unemployment < previous_unemployment:
        return "Improving"
    return "Stable"
