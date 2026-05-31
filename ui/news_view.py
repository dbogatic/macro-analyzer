from __future__ import annotations

import streamlit as st


def render_news(headlines: list[dict]) -> None:
    with st.expander("Current News Context", expanded=True):
        if not headlines:
            st.caption(
                "No headlines loaded. Add NEWSAPI_KEY to your .env file to enable live news context."
            )
            return
        for h in headlines:
            st.markdown(f"**{h['title']}**  \n*{h['source']} — {h['published']}*")
            st.divider()
