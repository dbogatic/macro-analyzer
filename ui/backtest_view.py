from __future__ import annotations

import streamlit as st

from backtesting.evaluator import extract_downside_prob, evaluate_trend
from backtesting.historical_cases import HISTORICAL_CASES
from backtesting.plots import plot_downside
from backtesting.runner import run_backtest

# HY spread (BAMLH0A0HYM2) is restricted to ~3 years on the free FRED API tier.
# Cases that fall outside that window run without the financial constraint signal.
_HY_SPREAD_AVAILABLE = {"inflation_cycle"}

_SIGNAL_NOTES = {
    "gfc": (
        "info",
        "Credit spread uses a proxy for this period: Moody's Baa–10y Treasury spread scaled to HY-equivalent units. "
        "The free FRED data tier restricts the standard HY spread series to recent years only. "
        "The proxy tracks the same credit risk premium at investment-grade quality — direction and regime shifts "
        "are reliable, though the absolute levels will differ from what the actual HY spread would have shown."
    ),
    "soft_landing": (
        "info",
        "Credit spread uses a proxy for this period (Baa–10y, same as GFC). "
        "Impact is minimal — credit conditions were calm during 2018–2019 regardless of which measure is used. "
        "All other signals (yield curve, unemployment, VIX, PCE) are fully available."
    ),
    "inflation_cycle": (
        "success",
        "All data signals are available for this period including the actual HY spread. "
        "This is the most complete and reliable backtest."
    ),
}


def render_backtest() -> None:
    st.subheader("Backtesting")
    case_key = st.selectbox("Case", list(HISTORICAL_CASES.keys()))

    level, note = _SIGNAL_NOTES.get(case_key, ("info", ""))
    if level == "warning":
        st.warning(note)
    elif level == "success":
        st.success(note)
    else:
        st.info(note)

    if st.button("Run backtest"):
        results = run_backtest(HISTORICAL_CASES[case_key])
        df = extract_downside_prob(results)
        trend = evaluate_trend(df)

        if "error" in trend:
            st.error(trend["error"])
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Start", f"{trend['start']:.0%}")
            col2.metric("End", f"{trend['end']:.0%}")
            col3.metric("Change", f"{trend['change']:+.0%}")
            st.plotly_chart(plot_downside(df, HISTORICAL_CASES[case_key]["name"]), use_container_width=True)
