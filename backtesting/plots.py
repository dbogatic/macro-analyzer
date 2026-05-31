from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def plot_downside(df: pd.DataFrame, title: str = "Downside Probability") -> go.Figure:
    rolling = df["downside_prob"].rolling(window=3, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["downside_prob"],
        mode="lines", name="Monthly",
        line=dict(color="steelblue", width=1),
        opacity=0.35,
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=rolling,
        mode="lines", name="3-month avg",
        line=dict(color="steelblue", width=2.5),
    ))
    fig.update_layout(
        title=title,
        xaxis_title="date",
        yaxis_title="downside_prob",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
