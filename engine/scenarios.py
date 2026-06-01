from __future__ import annotations

from engine.scenario_probabilities import assign_probabilities
from engine.scenario_templates import SCENARIO_TEMPLATES


def build_scenarios(system_state: dict) -> list[dict]:
    probs = assign_probabilities(
        float(system_state["constraint_score"]),
        float(system_state["fragility_score"]),
        system_state["momentum"],
        regime=system_state.get("regime", "Stress"),
        constraint_scores=system_state.get("constraint_scores"),
        financial_trend=system_state.get("financial_trend"),
    )

    confidence = "Moderate" if system_state["regime"] != "Break" else "Low-Moderate"

    return [
        {
            "type": "base",
            "name": SCENARIO_TEMPLATES["base"]["name"],
            "description": SCENARIO_TEMPLATES["base"]["description"],
            "probability": probs["base"],
            "confidence": confidence,
        },
        {
            "type": "upside",
            "name": SCENARIO_TEMPLATES["upside"]["name"],
            "description": SCENARIO_TEMPLATES["upside"]["description"],
            "probability": probs["upside"],
            "confidence": "Moderate",
        },
        {
            "type": "downside",
            "name": SCENARIO_TEMPLATES["downside"]["name"],
            "description": SCENARIO_TEMPLATES["downside"]["description"],
            "probability": probs["downside"],
            "confidence": "Low-Moderate",
        },
    ]
