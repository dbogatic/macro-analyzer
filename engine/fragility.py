from __future__ import annotations

import math

from config.calibration import CALIBRATION


def _number_or_none(data: dict, key: str) -> float | None:
    """A missing or non-finite reading is unknown, not a benign observation."""
    value = data.get(key)
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def score_fragility(data: dict) -> dict[str, int | None]:
    """Score observed fragility inputs; preserve missing components as None.

    A term-spread inversion is NOT evidence of stock-bond return-correlation
    breakdown. Correlation must be measured from asset returns separately.
    """
    hy = _number_or_none(data, "hy_spread")
    vix = _number_or_none(data, "vix")
    oil = _number_or_none(data, "oil")
    gold_yoy = _number_or_none(data, "gold")
    debt_service = _number_or_none(data, "debt_service")

    ds_mod = CALIBRATION["debt_service"]["moderate"]
    ds_high = CALIBRATION["debt_service"]["high"]
    vix_mod = CALIBRATION["vix"]["moderate"]
    vix_high = CALIBRATION["vix"]["high"]
    oil_mod = CALIBRATION["oil"]["moderate"]
    oil_sev = CALIBRATION["oil"]["severe"]
    gold_mod = CALIBRATION["gold_yoy"]["moderate"]
    gold_high = CALIBRATION["gold_yoy"]["high"]

    leverage = (None if debt_service is None else
                2 if debt_service > ds_high else
                1 if debt_service > ds_mod else 0)
    # HY and VIX both contribute to the combined liquidity score.
    # Unknown VIX is not evidence of an absence of market stress.
    liquidity = (None if hy is None or vix is None else
                 max(2 if hy > 6 else 1 if hy > 4 else 0,
                     2 if vix > vix_high else 1 if vix > vix_mod else 0))
    energy = (None if oil is None else
              2 if oil > oil_sev else 1 if oil > oil_mod else 0)
    institutional = (None if gold_yoy is None else
                     2 if gold_yoy > gold_high else 1 if gold_yoy > gold_mod else 0)

    return {
        "leverage": leverage,
        "liquidity": liquidity,
        "energy_dependency": energy,
        "institutional": institutional,
    }


def missing_fragility_components(scores: dict[str, int | None]) -> list[str]:
    return [name for name, value in scores.items() if value is None]
