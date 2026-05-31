from __future__ import annotations

from datetime import datetime

import streamlit as st


def render_sidebar(shock_suggestion: dict | None = None) -> dict:
    st.sidebar.header("Analysis Inputs")
    topic = st.sidebar.text_input("Topic", "U.S. macro / Fed outlook")
    horizon = st.sidebar.selectbox("Horizon", ["Immediate", "Short", "Medium", "Long"], index=1)
    report_mode = st.sidebar.selectbox("Report mode", ["short", "long"], index=0)

    # ── Custom news keywords ──────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Additional News Keywords**")
    st.sidebar.caption(
        "Add keywords to capture events the default query may miss — "
        "e.g. a country name, a specific conflict, a chokepoint. "
        "Separate multiple terms with commas."
    )
    extra_keywords_raw = st.sidebar.text_input("Extra keywords (optional)", "")
    extra_keywords = [k.strip() for k in extra_keywords_raw.split(",") if k.strip()]

    if st.sidebar.button("Refresh News", help="Re-fetch headlines with your keywords and update the shock suggestion"):
        from config.settings import settings
        from data.loaders.news_loader import fetch_macro_headlines
        from llm.shock_classifier import classify_shock

        if not settings.newsapi_key:
            st.session_state["_refresh_msg"] = ("error", "NEWSAPI_KEY not set.")
        else:
            # Step 1: fetch headlines
            try:
                with st.spinner("Fetching headlines..."):
                    headlines = fetch_macro_headlines(settings.newsapi_key, extra_keywords=extra_keywords)
                st.session_state["headlines"] = headlines
            except Exception as e:
                headlines = []
                st.session_state["_refresh_msg"] = ("error", f"News fetch failed: {e}")
                st.rerun()

            if not headlines:
                st.session_state["_refresh_msg"] = ("error", "No headlines returned — check NEWSAPI_KEY or try different keywords.")
            elif not settings.openai_api_key:
                n = len(headlines)
                st.session_state["_refresh_msg"] = ("warn", f"{n} headlines fetched but OpenAI key not set — cannot classify.")
            else:
                # Step 2: classify
                try:
                    with st.spinner("Classifying..."):
                        result = classify_shock(headlines)
                    if result:
                        st.session_state["shock_suggestion"] = result
                        st.session_state["_shock_refreshed_at"] = datetime.now().strftime("%H:%M:%S")
                        st.session_state["_shock_level_override"] = result.get("level", "None")
                        n = len(headlines)
                        st.session_state["_refresh_msg"] = (
                            "success",
                            f"{n} headlines fetched. Suggested: **{result.get('level')}** — {result.get('reason', '')}"
                        )
                    else:
                        st.session_state["_refresh_msg"] = ("error", "Classifier returned no result.")
                except Exception as e:
                    st.session_state["_refresh_msg"] = ("error", f"Classifier failed: {e}")
        st.rerun()

    # Show refresh outcome (stored before rerun, displayed after)
    if "_refresh_msg" in st.session_state:
        status, msg = st.session_state.pop("_refresh_msg")
        if status == "success":
            st.sidebar.success(msg)
        elif status == "warn":
            st.sidebar.warning(msg)
        else:
            st.sidebar.error(msg)

    # ── Energy/geopolitical shock override ───────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Energy / Geopolitical Shock Override**")
    st.sidebar.caption(
        "FRED data and market signals (VIX, oil, gold) are backward-looking — "
        "they reflect what has already happened. This override lets you inject "
        "a forward-looking geopolitical judgment for events that have not yet "
        "moved market prices: a war breaking out, new sanctions announced, a "
        "pipeline shutdown, or an escalation that oil markets haven't priced in yet.\n\n"
        "**None** — No active disruption. Model relies entirely on data signals.\n\n"
        "**Moderate** — Elevated tension or uncertainty not yet in prices. "
        "Raises energy/geo weight by ~5%. Use for: tariff uncertainty, "
        "regional conflict not affecting supply, mild oil concerns.\n\n"
        "**Severe** — Active disruption with clear supply impact. "
        "Raises energy/geo weight by ~10%. Use for: conflict affecting energy "
        "infrastructure, major sanctions, imminent supply shock."
    )

    # Show LLM suggestion box — read directly from session state so it always reflects the latest refresh
    current_suggestion = st.session_state.get("shock_suggestion")
    if current_suggestion:
        level = current_suggestion.get("level", "None")
        reason = current_suggestion.get("reason", "")
        refreshed_at = st.session_state.get("_shock_refreshed_at", "")
        timestamp = f"  \n*Last updated: {refreshed_at}*" if refreshed_at else ""
        if level != "None":
            st.sidebar.info(f"**News suggests: {level}**\n\n{reason}\n\n*You can change this below.*{timestamp}")
        else:
            st.sidebar.success(f"**News suggests: No active shock**\n\n{reason}{timestamp}")

    # Seed radio on first load from suggestion; override from refresh takes precedence
    SHOCK_OPTIONS = ["None", "Moderate", "Severe"]
    if "_shock_level_override" in st.session_state:
        default_level = st.session_state.pop("_shock_level_override")
    elif shock_suggestion and "shock_radio" not in st.session_state:
        default_level = shock_suggestion.get("level", "None")
    else:
        default_level = st.session_state.get("shock_radio", "None")

    shock_level = st.sidebar.radio(
        "Select shock level",
        options=SHOCK_OPTIONS,
        index=SHOCK_OPTIONS.index(default_level),
        key="shock_radio",
    )

    shock = None
    if shock_level == "Severe":
        shock = {"type": "energy_geo", "energy_disruption": "severe"}
    elif shock_level == "Moderate":
        shock = {"type": "energy_geo", "energy_disruption": "moderate"}

    return {
        "topic": topic,
        "horizon": horizon,
        "report_mode": report_mode,
        "shock": shock,
        "extra_keywords": extra_keywords,
    }
