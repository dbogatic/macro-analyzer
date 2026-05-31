from __future__ import annotations

import streamlit as st

from backtesting.evaluator import extract_downside_prob, evaluate_trend
from backtesting.historical_cases import HISTORICAL_CASES
from backtesting.plots import plot_downside
from backtesting.runner import run_backtest


def render_backtest() -> None:
    st.subheader("Backtesting")
    case_key = st.selectbox("Case", list(HISTORICAL_CASES.keys()))
    if st.button("Run backtest"):
        results = run_backtest(HISTORICAL_CASES[case_key])
        df = extract_downside_prob(results)
        trend = evaluate_trend(df)
        col1, col2, col3 = st.columns(3)
        col1.metric("Start", f"{trend['start']:.0%}")
        col2.metric("End", f"{trend['end']:.0%}")
        col3.metric("Change", f"{trend['change']:+.0%}")
        st.plotly_chart(plot_downside(df, HISTORICAL_CASES[case_key]["name"]), use_container_width=True)
