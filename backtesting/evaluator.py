from __future__ import annotations

import pandas as pd


def extract_downside_prob(results: list[dict]) -> pd.DataFrame:
    rows = []
    for result in results:
        for scenario in result["scenarios"]:
            if "Downside" in scenario["name"]:
                rows.append({
                    "date": result["date"],
                    "downside_prob": sum(scenario["probability"]) / 2,
                })
    return pd.DataFrame(rows)


def evaluate_trend(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"error": "No downside scenario data."}
    return {
        "start": float(df["downside_prob"].iloc[0]),
        "end": float(df["downside_prob"].iloc[-1]),
        "change": float(df["downside_prob"].iloc[-1] - df["downside_prob"].iloc[0]),
    }
