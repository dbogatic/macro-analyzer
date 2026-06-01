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


_REQUIRED_COLS = {"core_pce", "unemployment", "2y", "10y"}
_TREND_WINDOW  = 3   # months for financial trend delta
_HY_THRESHOLD  = 0.5
_CURVE_THRESHOLD = 0.2


def _compute_financial_trend(df, idx: int) -> dict | None:
    """Compute 3-month HY spread and yield curve trend at position idx in df."""
    if idx < _TREND_WINDOW:
        return None
    try:
        hy_delta    = df["hy_spread"].iloc[idx] - df["hy_spread"].iloc[idx - _TREND_WINDOW]
        y2_delta    = df["2y"].iloc[idx]        - df["2y"].iloc[idx - _TREND_WINDOW]
        y10_delta   = df["10y"].iloc[idx]       - df["10y"].iloc[idx - _TREND_WINDOW]
        curve_delta = y10_delta - y2_delta

        hy_trend = (
            "Widening"   if hy_delta >  _HY_THRESHOLD    else
            "Tightening" if hy_delta < -_HY_THRESHOLD    else
            "Stable"
        )
        curve_trend = (
            "Normalizing" if curve_delta >  _CURVE_THRESHOLD else
            "Inverting"   if curve_delta < -_CURVE_THRESHOLD else
            "Stable"
        )
        return {"hy_trend": hy_trend, "curve_trend": curve_trend}
    except Exception:
        return None


def run_backtest(case: dict) -> list[dict]:
    df = load_dataset(case["start"], case["end"])

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise RuntimeError(
            f"Backtest data is missing required series: {sorted(missing)}. "
            "FRED may be down or rate-limiting — wait a moment and retry."
        )

    # Forward-fill gaps (e.g. quarterly series like TDSP, sparse daily series
    # resampled to monthly) then drop any rows still missing required columns.
    df = df.ffill().dropna(subset=list(_REQUIRED_COLS))

    results: list[dict] = []
    prev_unemployment = None

    for idx, (date, row) in enumerate(df.iterrows()):
        data = row.to_dict()
        constraint_scores = build_constraint_scores(data)
        fragility_scores = score_fragility(data)
        constraint_total = float(sum(constraint_scores.values()))
        fragility_total = float(sum(fragility_scores.values()))
        # 3-month unemployment trend from the historical DataFrame
        if idx >= _TREND_WINDOW and "unemployment" in df.columns:
            u_delta = df["unemployment"].iloc[idx] - df["unemployment"].iloc[idx - _TREND_WINDOW]
            unemployment_3m_trend = (
                "Rising"  if u_delta >  0.1 else
                "Falling" if u_delta < -0.1 else
                "Stable"
            )
        else:
            unemployment_3m_trend = None

        momentum = classify_momentum(
            float(data["unemployment"]),
            prev_unemployment,
            unemployment_3m_trend=unemployment_3m_trend,
        )
        prev_unemployment = float(data["unemployment"])
        regime, classification = classify_regime(constraint_total, fragility_total, momentum)
        weights, rationale = adjust_weights(BASE_WEIGHTS, constraint_scores, fragility_scores, regime, raw_data=data)
        financial_trend = _compute_financial_trend(df, idx)
        scenarios = build_scenarios({
            "constraint_score":  constraint_total,
            "fragility_score":   fragility_total,
            "momentum":          momentum,
            "regime":            regime,
            "constraint_scores": constraint_scores,
            "financial_trend":   financial_trend,
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
