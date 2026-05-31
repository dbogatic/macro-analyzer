from __future__ import annotations

from backtesting.data_loader import load_dataset
from config.base_weights import BASE_WEIGHTS
from engine.auto_scoring import build_constraint_scores
from engine.fragility import score_fragility
from engine.momentum import classify_momentum
from engine.normalization import finalize_scenarios
from engine.regime import classify_regime
from engine.scenarios import build_scenarios
from engine.weighting import adjust_weights


_REQUIRED_COLS = {"core_pce", "unemployment", "hy_spread", "2y", "10y"}


def run_backtest(case: dict) -> list[dict]:
    df = load_dataset(case["start"], case["end"])

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise RuntimeError(
            f"Backtest data is missing required series: {sorted(missing)}. "
            "FRED may be down or rate-limiting — wait a moment and retry."
        )

    results: list[dict] = []
    prev_unemployment = None

    for date, row in df.iterrows():
        data = row.to_dict()
        constraint_scores = build_constraint_scores(data)
        fragility_scores = score_fragility(data)
        constraint_total = float(sum(constraint_scores.values()))
        fragility_total = float(sum(fragility_scores.values()))
        momentum = classify_momentum(float(data["unemployment"]), prev_unemployment)
        prev_unemployment = float(data["unemployment"])
        regime, classification = classify_regime(constraint_total, fragility_total, momentum)
        weights, rationale = adjust_weights(BASE_WEIGHTS, constraint_scores, fragility_scores, regime, raw_data=data)
        scenarios = build_scenarios({
            "constraint_score": constraint_total,
            "fragility_score": fragility_total,
            "momentum": momentum,
            "regime": regime,
        })
        scenarios, errors = finalize_scenarios(scenarios, fragility_total)
        results.append({
            "date": date,
            "constraint_score": constraint_total,
            "fragility_score": fragility_total,
            "momentum": momentum,
            "regime": regime,
            "classification": classification,
            "weights": weights,
            "weight_rationale": rationale,
            "scenarios": scenarios,
            "errors": errors,
        })
    return results
