from __future__ import annotations


def midpoint(prob_range: tuple[float, float]) -> float:
    return (prob_range[0] + prob_range[1]) / 2


def normalize_scenarios(scenarios: list[dict]) -> list[dict]:
    mids = [midpoint(s["probability"]) for s in scenarios]
    total = sum(mids)
    if total <= 0:
        return scenarios

    normalized = []
    for scenario, mid in zip(scenarios, mids):
        weight = mid / total
        width = scenario["probability"][1] - scenario["probability"][0]
        low = max(0.0, weight - width / 2)
        high = min(1.0, weight + width / 2)
        normalized.append({**scenario, "probability": (round(low, 3), round(high, 3))})
    return normalized


def enforce_tail_risk(scenarios: list[dict], fragility_score: float) -> list[dict]:
    if fragility_score < 7:
        return scenarios
    adjusted = []
    for scenario in scenarios:
        low, high = scenario["probability"]
        if "Downside" in scenario["name"]:
            low = max(low, 0.15)
            high = max(high, 0.20)
        adjusted.append({**scenario, "probability": (low, high)})
    return adjusted


def finalize_scenarios(scenarios: list[dict], fragility_score: float) -> tuple[list[dict], list[str]]:
    scenarios = enforce_tail_risk(scenarios, fragility_score)
    scenarios = normalize_scenarios(scenarios)
    errors = []
    for scenario in scenarios:
        low, high = scenario["probability"]
        if low < 0 or high < 0:
            errors.append(f"{scenario['name']} has negative probability")
        if low > high:
            errors.append(f"{scenario['name']} has invalid range")
        if high > 1:
            errors.append(f"{scenario['name']} exceeds 100%")
    return scenarios, errors
