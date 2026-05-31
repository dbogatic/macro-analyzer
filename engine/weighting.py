from __future__ import annotations

from typing import Any

from config.calibration import CALIBRATION


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {k: round(v / total, 4) for k, v in weights.items()}


def adjust_weights(
    base_weights: dict[str, float],
    constraint_scores: dict[str, int],
    fragility_scores: dict[str, int],
    regime: str,
    shock: dict[str, Any] | None = None,
    raw_data: dict[str, Any] | None = None,
) -> tuple[dict[str, float], list[str]]:
    weights = base_weights.copy()
    rationale: list[str] = []

    # ── Constraint-driven adjustments ────────────────────────────────────────
    if constraint_scores.get("policy") == 2:
        weights["policy"] += 0.05
        rationale.append("Policy constraint binding -> policy weight increased")
    if constraint_scores.get("growth") == 2:
        weights["growth"] += 0.05
        rationale.append("Growth stress elevated -> growth weight increased")
    if constraint_scores.get("financial") == 2:
        weights["financial"] += 0.05
        rationale.append("Financial stress elevated -> financial weight increased")
    if fragility_scores.get("liquidity") == 2:
        weights["financial"] += 0.05
        rationale.append("Liquidity fragility high -> financial weight increased")

    # ── VIX-driven adjustment (crisis level only — moderate already via fragility) ──
    # Liquidity fragility path captures VIX > 20; this fires only at crisis (> 30).
    if raw_data:
        vix = float(raw_data.get("vix", 0))
        vix_high = CALIBRATION["vix"]["high"]
        if vix > vix_high:
            weights["financial"] += 0.05
            rationale.append(f"VIX at {vix:.1f} (crisis > {vix_high}) -> financial weight increased")

    # ── Gold-driven adjustment (institutional risk-off signal) ────────────────
    if raw_data:
        gold_yoy = float(raw_data.get("gold", 0))
        gold_mod  = CALIBRATION["gold_yoy"]["moderate"]
        gold_high = CALIBRATION["gold_yoy"]["high"]
        if gold_yoy > gold_high:
            weights["financial"] += 0.10
            rationale.append(f"Gold YoY {gold_yoy:.1f}% (crisis > {gold_high}%) -> financial weight increased")
        elif gold_yoy > gold_mod:
            weights["financial"] += 0.05
            rationale.append(f"Gold YoY {gold_yoy:.1f}% (elevated > {gold_mod}%) -> financial weight increased")

    # ── Oil-driven energy/geo adjustment (data-driven, takes precedence) ─────
    # Oil price feeds directly into energy_geo weight.
    # Manual shock override applies only when oil data is not signalling.
    oil_adjustment_applied = False
    if raw_data:
        oil = float(raw_data.get("oil", 0))
        if oil > CALIBRATION["oil"]["severe"]:
            weights["energy_geo"] += 0.10
            rationale.append(f"Oil at ${oil:.0f}/bbl (above ${CALIBRATION['oil']['severe']}) -> energy/geo weight increased")
            oil_adjustment_applied = True
        elif oil > CALIBRATION["oil"]["moderate"]:
            weights["energy_geo"] += 0.05
            rationale.append(f"Oil at ${oil:.0f}/bbl (above ${CALIBRATION['oil']['moderate']}) -> energy/geo weight increased")
            oil_adjustment_applied = True

    # ── Manual shock override (applies when oil data is not signalling) ───────
    if not oil_adjustment_applied and shock:
        if shock.get("energy_disruption") == "severe":
            weights["energy_geo"] += 0.10
            rationale.append("Severe energy disruption (manual override) -> energy/geo weight increased")
        elif shock.get("energy_disruption") == "moderate":
            weights["energy_geo"] += 0.05
            rationale.append("Moderate energy disruption (manual override) -> energy/geo weight increased")

    # ── Regime-driven adjustments ─────────────────────────────────────────────
    if regime == "Break":
        weights["financial"] += 0.05
        weights["policy"] += 0.05
        rationale.append("Break regime -> policy and financial weights increased")
    elif regime == "Policy response":
        weights["policy"] += 0.05
        rationale.append("Policy response regime -> policy weight increased")

    return normalize_weights(weights), rationale
