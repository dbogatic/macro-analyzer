from __future__ import annotations

from datetime import datetime, timedelta

from config.fred_series import FRED_SERIES
from data.loaders.fred_loader import load_dataset as load_fred_dataset
from data.loaders.stooq_loader import get_gld_history

# Market signals available via FRED for historical backtesting.
BACKTEST_MARKET_SIGNALS = {
    "vix": "VIXCLS",
    "oil": "DCOILWTICO",
}


def load_dataset(start: str, end: str):
    all_series = {**FRED_SERIES, **BACKTEST_MARKET_SIGNALS}
    df = load_fred_dataset(all_series, start, end)

    # Gold: FRED series are discontinued — fetch GLD ETF history from Yahoo Finance.
    # Pull 13 months before start so pct_change(12) is valid for the first window month.
    extended_start = (datetime.strptime(start, "%Y-%m-%d") - timedelta(days=400)).strftime("%Y-%m-%d")
    gld = get_gld_history(extended_start, end)
    if gld is not None and not gld.empty:
        gld_monthly = gld.resample("ME").last().dropna()
        gld_yoy = gld_monthly.pct_change(12) * 100
        df["gold"] = gld_yoy.reindex(df.index)

    return df
