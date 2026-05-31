from __future__ import annotations

from typing import Any


def build_llm_payload(
    topic: str,
    horizon: str,
    system_state: dict[str, Any],
    weights: dict[str, float],
    weight_rationale: list[str],
    scenarios: list[dict[str, Any]],
    triggers: list[dict[str, Any]],
    data_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "topic": topic,
        "horizon": horizon,
        "data_snapshot": data_snapshot,
        "system_state": system_state,
        "weights": weights,
        "weight_rationale": weight_rationale,
        "scenarios": scenarios,
        "triggers": triggers,
    }
