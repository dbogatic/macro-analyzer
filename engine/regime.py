from __future__ import annotations


def classify_regime(constraint_total: float, fragility_total: float, momentum: str) -> tuple[str, str]:
    if constraint_total >= 7 or fragility_total >= 7:
        regime = "Break"
        classification = "Iceberg Risk"
    elif momentum in {"Stable", "Improving"} and constraint_total <= 4 and fragility_total <= 4:
        regime = "Stabilization"
        classification = "Smooth"
    else:
        regime = "Stress"
        classification = "Turbulence"
    return regime, classification
