from __future__ import annotations

import pandas as pd


def volatility(df: pd.DataFrame) -> float:
    if df.empty or len(df) < 2:
        return 0.0
    return float(df["downside_prob"].diff().abs().mean())
