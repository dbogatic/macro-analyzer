# COVID (2019-2021) is intentionally excluded from backtest cases.
# Rationale: exogenous supply shock with no macro imbalance buildup.
# The model's thresholds were calibrated without COVID data for the same
# reason — including it as a backtest case would test the model against
# conditions it was explicitly not designed to handle, producing
# misleading validation results. See README for full methodology.

HISTORICAL_CASES = {
    "gfc": {"name": "Global Financial Crisis", "start": "2007-01-01", "end": "2009-12-31"},
    "inflation_cycle": {"name": "Inflation / Tightening", "start": "2021-01-01", "end": "2023-12-31"},
    "soft_landing": {"name": "Soft Landing / Insurance Cuts", "start": "2018-01-01", "end": "2019-12-31"},
}
