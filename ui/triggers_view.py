from __future__ import annotations

import pandas as pd
import streamlit as st


def render_triggers(triggers: list[dict]) -> None:
    st.subheader("Triggers")
    st.dataframe(pd.DataFrame(triggers), use_container_width=True)
    fired = [t for t in triggers if t.get("fired")]
    if fired:
        st.warning(f"{len(fired)} trigger(s) fired")
