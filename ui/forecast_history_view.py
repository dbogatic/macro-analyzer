"""Read-only Forecast Validation page for Macro Analyzer 2.0.

No predictions are created in this view. The legacy scenario weights are
not statistical forecasts and are intentionally excluded.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from data.storage.forecast_evaluation import evaluate_binary, evaluate_continuous
from data.storage.forecast_queries import (
    list_forecast_history, list_models, list_outcome_revisions, list_targets,
)


def render_forecast_history(db_path: str) -> None:
    st.subheader("Forecast Validation")
    st.caption(
        "Only registered model forecasts are shown. Legacy rule-based scenario "
        "percentages are not calibrated predictions."
    )
    targets = list_targets(db_path)
    if not targets:
        st.info(
            "Forecast database initialized. No statistical forecasts have been "
            "registered yet; predictive performance cannot be evaluated."
        )
        return

    target = st.selectbox("Forecast target", targets, key="validation_target")
    model_choices = list_models(db_path, target)
    if not model_choices:
        st.info("No models registered for this target.")
        return
    model_label = {
        f"{name}  |  version {version}": (name, version)
        for name, version in model_choices
    }
    label = st.selectbox("Model and version", list(model_label), key="validation_model")
    model_name, model_version = model_label[label]

    revisions = list_outcome_revisions(db_path, target, model_name, model_version)
    selected_source = None
    if revisions:
        rev_labels = {
            f"{source}  |  version {version}": (source, version)
            for source, version in revisions
        }
        revision_label = st.selectbox(
            "Realized outcome source and version",
            list(rev_labels), key="validation_outcome_revision",
        )
        selected_source = rev_labels[revision_label]
    else:
        st.warning(
            "No actual outcomes recorded for this model yet. "
            "Performance metrics require realized outcomes."
        )

    kwargs = {}
    if selected_source is not None:
        kwargs = {
            "source_name": selected_source[0],
            "source_version": selected_source[1],
        }
    history = list_forecast_history(
        db_path, target, model_name, model_version, **kwargs,
    )
    total = len(history)
    evaluated = [row for row in history if row["outcome"] is not None]
    pending = total - len(evaluated)
    a, b, c = st.columns(3)
    a.metric("Issued forecasts", total)
    b.metric("Outcomes matched", len(evaluated))
    c.metric("Without matched outcome", pending)

    if history:
        frame = pd.DataFrame(history)
        frame["outcome_status"] = frame["outcome"].apply(
            lambda value: "Matched" if pd.notna(value) else "Pending / unavailable"
        )
        st.dataframe(frame, use_container_width=True, hide_index=True)

    if not evaluated:
        st.info("Accuracy statistics are not available until outcomes are matched.")
        return

    kinds = {row["kind"] for row in evaluated}
    if len(kinds) != 1:
        st.error("Mixed forecast kinds: cannot calculate a combined accuracy score.")
        return
    kind = kinds.pop()
    if kind == "binary":
        score = evaluate_binary(evaluated)
        st.metric("Brier score (lower is better)", f"{score['brier']:.4f}")
        st.metric("Log loss (lower is better)", f"{score['log_loss']:.4f}")
    elif kind == "continuous":
        score = evaluate_continuous(evaluated)
        st.metric("Mean absolute error", f"{score['mae']:.4f}")
        st.metric("Root mean squared error", f"{score['rmse']:.4f}")
        if score["interval_n"]:
            st.metric(
                "Observed interval coverage",
                f"{score['interval_coverage']:.1%}",
            )
            st.caption(
                f"Interval coverage is based on {score['interval_n']} forecasts; "
                "the nominal interval level is not recorded in the current schema."
            )
    else:
        st.error(f"Unsupported forecast kind: {kind}")
        return

    st.caption(
        "Descriptive scores only. No out-of-sample skill, calibration, "
        "statistical significance, or superiority over a benchmark has yet "
        "been established. Missing outcomes are not counted as correct."
    )
