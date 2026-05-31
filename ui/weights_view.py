from __future__ import annotations

import pandas as pd
import streamlit as st


def render_weights(base: dict, current: dict, rationale: list[str]) -> None:
    rows = []
    for key, base_weight in base.items():
        rows.append({
            "Module": key,
            "Base": base_weight,
            "Current": current.get(key, 0.0),
            "Change": round(current.get(key, 0.0) - base_weight, 4),
        })
    st.subheader("Weights")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    if rationale:
        st.caption("Weight rationale")
        for item in rationale:
            st.write(f"- {item}")
