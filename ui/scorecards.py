from __future__ import annotations

import pandas as pd
import streamlit as st


def render_scorecards(constraint_scores: dict, fragility_scores: dict) -> None:
    st.subheader("Constraint Pressure")
    st.dataframe(pd.DataFrame({"Component": list(constraint_scores.keys()), "Score": list(constraint_scores.values())}), use_container_width=True)

    st.subheader("Fragility")
    st.dataframe(pd.DataFrame({"Component": list(fragility_scores.keys()), "Score": list(fragility_scores.values())}), use_container_width=True)
