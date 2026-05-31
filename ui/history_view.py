from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from data.storage.sqlite_store import clear_runs, load_runs


def render_history(limit: int = 20) -> None:
    rows = load_runs(limit)
    if not rows:
        st.info("No saved runs yet.")
        return

    if st.button("Clear all runs", type="secondary"):
        n = clear_runs()
        st.success(f"Deleted {n} run(s).")
        st.rerun()
    formatted = []
    for row in rows:
        formatted.append({
            "timestamp": row["timestamp"],
            "topic": row["topic"],
            "horizon": row["horizon"],
            "report_mode": row["report_mode"],
            "constraint": row["constraint_score"],
            "fragility": row["fragility_score"],
            "regime": row["regime"],
            "classification": row["classification"],
        })
    st.subheader("Run History")
    st.dataframe(pd.DataFrame(formatted), use_container_width=True)
