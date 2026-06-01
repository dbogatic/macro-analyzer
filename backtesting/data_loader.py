from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from config.fred_series import FRED_SERIES
from data.loaders.fred_loader import load_dataset as load_fred_dataset, load_series_range
from data.loaders.stooq_loader import get_gld_history

# Market signals available via FRED for historical backtesting.
BACKTEST_MARKET_SIGNALS = {
    "vix": "VIXCLS",
    "oil": "DCOILWTICO",
}

# BAMLH0A0HYM2 is restricted to ~3 years on the free FRED API tier.
# For older periods we fall back to the Moody's Baa–10y Treasury spread,
# which measures the same credit risk premium at investment-grade quality.
# Scaling factor 3.5 maps it to approximate HY-spread equivalence so the
# existing scoring thresholds (moderate 3.89%, high 7.0%) fire correctly.
_HY_PROXY_SCALE = 3.5


def _load_hy_proxy(start: str, end: str) -> pd.Series | None:
    """Return Baa–10y spread scaled to HY-equivalent units, or None on failure."""
    try:
        baa = load_series_range("BAA",   start, end).resample("ME").last()
        dgs = load_series_range("DGS10", start, end).resample("ME").last()
        proxy = (baa - dgs) * _HY_PROXY_SCALE
        return proxy.dropna()
    except Exception:
        return None


def load_dataset(start: str, end: str):
    all_series = {**FRED_SERIES, **BACKTEST_MARKET_SIGNALS}
    # Load 13 extra months before the requested start so that pct_change(12)
    # produces valid YoY values from the very first month of the period.
    extended_start = (datetime.strptime(start, "%Y-%m-%d") - timedelta(days=400)).strftime("%Y-%m-%d")
    df = load_fred_dataset(all_series, extended_start, end)
    # Trim back to the requested start after YoY transformation is applied.
    df = df[df.index >= pd.Timestamp(start)]

    # Fill missing HY spread values with the Baa–10y proxy.
    # BAMLH0A0HYM2 is restricted to ~3 years on the free FRED tier, so any
    # months outside that window will be NaN. The proxy fills those gaps so
    # the financial constraint signal works across all backtest periods.
    proxy = _load_hy_proxy(start, end)
    if proxy is not None and not proxy.empty:
        proxy_aligned = proxy.reindex(df.index)
        if "hy_spread" not in df.columns:
            df["hy_spread"] = proxy_aligned
        else:
            df["hy_spread"] = df["hy_spread"].fillna(proxy_aligned)

    # Gold: FRED series are discontinued — fetch GLD ETF history from Yahoo Finance.
    gld = get_gld_history(extended_start, end)
    if gld is not None and not gld.empty:
        gld_monthly = gld.resample("ME").last().dropna()
        gld_yoy = gld_monthly.pct_change(12) * 100
        df["gold"] = gld_yoy.reindex(df.index)

    return df
