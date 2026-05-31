from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render_scenarios(scenarios: list[dict]) -> None:
    rows = []
    for s in scenarios:
        rows.append({
            "Scenario": s["name"],
            "Low": round(s["probability"][0] * 100, 1),
            "High": round(s["probability"][1] * 100, 1),
            "Confidence": s["confidence"],
        })
    df = pd.DataFrame(rows)
    st.subheader("Scenarios")
    st.dataframe(df, use_container_width=True)
    chart_df = pd.DataFrame({
        "Scenario": [s["name"] for s in scenarios],
        "Probability": [sum(s["probability"]) / 2 for s in scenarios],
    })
    fig = px.pie(chart_df, names="Scenario", values="Probability", title="Scenario Distribution")
    st.plotly_chart(fig, use_container_width=True)
