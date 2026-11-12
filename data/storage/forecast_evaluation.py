"""Descriptive scores for forecasts paired with realized outcomes.

Caller must select a consistent outcome revision and report sample coverage.
These functions do not prove predictive skill or statistical significance.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence


def evaluate_binary(rows: Sequence[Mapping]) -> dict:
    """Brier score and log loss for binary outcome forecasts."""
    if not rows:
        return {"n": 0, "brier": None, "log_loss": None}
    pairs = []
    for row in rows:
        p, y = float(row["prediction"]), float(row["outcome"])
        if not math.isfinite(p) or not 0 <= p <= 1 or y not in (0, 1):
            raise ValueError("Binary evaluation needs probabilities [0, 1] and outcomes 0/1")
        pairs.append((p, y))
    eps = 1e-15
    return {
        "n": len(pairs),
        "brier": sum((p-y)**2 for p, y in pairs) / len(pairs),
        "log_loss": -sum(
            y * math.log(max(eps, min(1-eps, p))) +
            (1-y) * math.log(max(eps, min(1-eps, 1-p)))
            for p, y in pairs
        ) / len(pairs),
    }


def evaluate_continuous(rows: Sequence[Mapping]) -> dict:
    """MAE, RMSE, and observed prediction-interval coverage."""
    if not rows:
        return {
            "n": 0, "mae": None, "rmse": None,
            "interval_n": 0, "interval_coverage": None,
        }
    errors, within = [], []
    for row in rows:
        pred, outcome = float(row["prediction"]), float(row["outcome"])
        if not math.isfinite(pred) or not math.isfinite(outcome):
            raise ValueError("Non-finite evaluation input")
        errors.append(pred - outcome)
        lo, hi = row["lower"], row["upper"]
        if (lo is None) != (hi is None):
            raise ValueError("Incomplete prediction interval")
        if lo is not None:
            lo, hi = float(lo), float(hi)
            if not math.isfinite(lo) or not math.isfinite(hi) or lo > hi:
                raise ValueError("Invalid prediction interval")
            within.append(lo <= outcome <= hi)
    return {
        "n": len(errors),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "rmse": math.sqrt(sum(e*e for e in errors) / len(errors)),
        "interval_n": len(within),
        "interval_coverage": sum(within) / len(within) if within else None,
    }
