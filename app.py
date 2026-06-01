from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config.base_weights import BASE_WEIGHTS
from config.fred_series import FRED_SERIES, MARKET_SIGNALS
from config.settings import APP_TITLE
from data.loaders.fred_loader import load_all_series, load_financial_trend, get_unemployment_3m_trend
from data.loaders.news_loader import fetch_macro_headlines
from data.loaders.stooq_loader import get_gld_data
from llm.shock_classifier import classify_shock
from data.storage.sqlite_store import init_db, save_run
from engine.auto_scoring import build_constraint_scores
from engine.fragility import score_fragility
from engine.momentum import classify_momentum
from engine.normalization import finalize_scenarios
from engine.regime import classify_regime
from engine.scenarios import build_scenarios
from engine.triggers import apply_trigger_adjustments, evaluate_triggers, triggers_to_dicts
from engine.weighting import adjust_weights
from exports.docx_export import export_docx
from exports.pdf_export import export_pdf
from llm.report_generator import generate_report
from llm.schemas import build_llm_payload
from ui.backtest_view import render_backtest
from ui.news_view import render_news
from ui.dashboard import render_dashboard
from ui.history_view import render_history
from ui.scenarios_view import render_scenarios
from ui.scorecards import render_scorecards
from config.settings import settings
from ui.sidebar import render_sidebar
from ui.triggers_view import render_triggers
from ui.weights_view import render_weights

init_db()
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# Fetch news once per session (no quant context yet — used to pre-fill sidebar before first run)
if "headlines" not in st.session_state:
    try:
        st.session_state["headlines"] = (
            fetch_macro_headlines(settings.newsapi_key) if settings.newsapi_key else []
        )
    except Exception:
        st.session_state["headlines"] = []
if "shock_suggestion" not in st.session_state:
    try:
        st.session_state["shock_suggestion"] = classify_shock(st.session_state["headlines"])
    except Exception:
        st.session_state["shock_suggestion"] = None

sidebar = render_sidebar(shock_suggestion=st.session_state["shock_suggestion"])

mode = st.radio("View", ["Analysis", "History", "Backtesting"], horizontal=True)

if mode == "History":
    render_history()
    st.stop()

if mode == "Backtesting":
    render_backtest()
    st.stop()


# Show headlines whenever they're available — persists across reruns and refreshes
if st.session_state.get("headlines"):
    render_news(st.session_state["headlines"])

if st.button("Run Analysis", type="primary"):
    # Re-fetch headlines with any extra keywords the user added, then
    # re-run the classifier with full quantitative context after data loads.
    extra_keywords = sidebar.get("extra_keywords", [])
    if settings.newsapi_key and extra_keywords:
        headlines = fetch_macro_headlines(settings.newsapi_key, extra_keywords=extra_keywords)
        st.session_state["headlines"] = headlines
    else:
        headlines = st.session_state.get("headlines", [])

    # Load required macro series — stop if any fail
    raw_data = load_all_series(FRED_SERIES)
    errors = [f"{k}: {v['error']}" for k, v in raw_data.items() if isinstance(v, dict) and v.get("error")]
    if errors:
        st.error("Could not load all required FRED data. Check FRED_API_KEY or network access.")
        st.write(errors)
        st.stop()

    # Load optional market signals — warn but continue if any fail
    market_data = load_all_series(MARKET_SIGNALS)
    for k, v in market_data.items():
        if isinstance(v, dict) and v.get("error"):
            st.warning(f"Market signal unavailable — {k}: {v['error']}")
        else:
            raw_data[k] = v


    # Gold via Yahoo Finance (GLD ETF — no API key required)
    gold_yoy, gold_price, gold_error = get_gld_data()
    if gold_yoy is not None:
        raw_data["gold"] = gold_yoy
        raw_data["gold_price"] = gold_price
    else:
        st.warning(f"Gold unavailable: {gold_error}")

    # Re-run shock classifier now that quantitative signals are available.
    # Oil at $114 firing the severe trigger is corroborating evidence the
    # initial headline-only pass couldn't see.
    updated_suggestion = classify_shock(headlines, quant_signals=raw_data)
    if updated_suggestion:
        st.session_state["shock_suggestion"] = updated_suggestion

    # Financial trend signals — direction of HY spread and yield curve over
    # the last 3 months. Optional: if FRED is unavailable the model continues
    # without trend adjustments.
    financial_trend = load_financial_trend()
    if financial_trend.get("error"):
        st.warning(f"Financial trend signals unavailable: {financial_trend['error']}")
        financial_trend = None

    constraint_scores = build_constraint_scores(raw_data)
    fragility_scores = score_fragility(raw_data)
    constraint_total = float(sum(constraint_scores.values()))
    fragility_total = float(sum(fragility_scores.values()))
    previous_unemployment = st.session_state.get("previous_unemployment")

    # Composite momentum: 3-month unemployment trend + jobless claims YoY.
    # Falls back gracefully if FRED is unavailable.
    try:
        unemployment_3m_trend = get_unemployment_3m_trend()
    except Exception:
        unemployment_3m_trend = None

    jobless_claims_yoy: float | None = None
    raw_claims = market_data.get("jobless_claims")
    if isinstance(raw_claims, (int, float)):
        jobless_claims_yoy = float(raw_claims)

    momentum = classify_momentum(
        float(raw_data["unemployment"]),
        previous_unemployment,
        unemployment_3m_trend=unemployment_3m_trend,
        jobless_claims_yoy=jobless_claims_yoy,
    )
    st.session_state["previous_unemployment"] = float(raw_data["unemployment"])
    regime, classification = classify_regime(constraint_total, fragility_total, momentum)
    current_weights, weight_rationale = adjust_weights(
        BASE_WEIGHTS, constraint_scores, fragility_scores, regime,
        shock=sidebar["shock"], raw_data=raw_data,
    )
    scenarios = build_scenarios(
        {
            "constraint_score":  constraint_total,
            "fragility_score":   fragility_total,
            "momentum":          momentum,
            "regime":            regime,
            "constraint_scores": constraint_scores,
            "financial_trend":   financial_trend,
        }
    )
    triggers = evaluate_triggers(raw_data)
    scenarios = apply_trigger_adjustments(scenarios, triggers, fragility_scores=fragility_scores)
    scenarios, scenario_errors = finalize_scenarios(scenarios, fragility_total)

    system_state = {
        "constraint_score": constraint_total,
        "fragility_score": fragility_total,
        "momentum": momentum,
        "regime": regime,
        "classification": classification,
        "constraint_scores": constraint_scores,
        "fragility_scores": fragility_scores,
        "scenario_errors": scenario_errors,
    }

    trigger_dicts = triggers_to_dicts(triggers)
    payload = build_llm_payload(
        topic=sidebar["topic"],
        horizon=sidebar["horizon"],
        system_state=system_state,
        weights=current_weights,
        weight_rationale=weight_rationale,
        scenarios=scenarios,
        triggers=trigger_dicts,
        data_snapshot=raw_data,
    )
    report_text = generate_report(payload, mode=sidebar["report_mode"], headlines=headlines)

    save_run(
        {
            "topic": sidebar["topic"],
            "horizon": sidebar["horizon"],
            "report_mode": sidebar["report_mode"],
            "constraint_score": constraint_total,
            "fragility_score": fragility_total,
            "momentum": momentum,
            "regime": regime,
            "classification": classification,
            "weights": current_weights,
            "scenarios": scenarios,
            "triggers": trigger_dicts,
            "payload": payload,
        }
    )

    render_dashboard(raw_data, classification, constraint_total, fragility_total)
    c1, c2 = st.columns(2)
    with c1:
        render_scorecards(constraint_scores, fragility_scores)
    with c2:
        render_weights(BASE_WEIGHTS, current_weights, weight_rationale)

    render_scenarios(scenarios)
    render_triggers(trigger_dicts)

    st.subheader("Report")
    st.text_area("Generated report", report_text, height=500)

    st.download_button("Download Markdown", report_text, file_name="macro_report.md", mime="text/markdown")

    tmp_dir = Path(".streamlit_tmp")
    tmp_dir.mkdir(exist_ok=True)
    docx_path = export_docx(report_text, tmp_dir / "macro_report.docx")
    with open(docx_path, "rb") as f:
        st.download_button("Download DOCX", f.read(), file_name=docx_path.name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    try:
        pdf_path = export_pdf(report_text, tmp_dir / "macro_report.pdf")
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f.read(), file_name=pdf_path.name, mime="application/pdf")
    except Exception as e:
        st.info(f"PDF export unavailable: {e}")

    with st.expander("Structured payload"):
        st.code(json.dumps(payload, indent=2, default=str), language="json")
else:
    st.info("Set your topic and horizon in the sidebar, then click Run Analysis.")
