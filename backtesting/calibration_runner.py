from __future__ import annotations

from backtesting.evaluator import extract_downside_prob
from backtesting.historical_cases import HISTORICAL_CASES
from backtesting.runner import run_backtest


def run_all_cases() -> dict:
    outputs = {}
    for key, case in HISTORICAL_CASES.items():
        outputs[key] = extract_downside_prob(run_backtest(case))
    return outputs
