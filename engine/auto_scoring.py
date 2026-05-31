from __future__ import annotations

from config.calibration import CALIBRATION


def score_policy_constraint(core_pce: float, unemployment: float) -> int:
    if core_pce >= CALIBRATION["core_pce"]["high"] and unemployment < 4.5:
        return 2
    if core_pce >= CALIBRATION["core_pce"]["moderate"]:
        return 1
    return 0


def score_growth_constraint(unemployment: float) -> int:
    if unemployment >= CALIBRATION["unemployment"]["high"]:
        return 2
    if unemployment >= CALIBRATION["unemployment"]["moderate"]:
        return 1
    return 0


def score_financial_constraint(hy_spread: float) -> int:
    if hy_spread >= CALIBRATION["hy_spread"]["high"]:
        return 2
    if hy_spread >= CALIBRATION["hy_spread"]["moderate"]:
        return 1
    return 0


def score_yield_curve(y2: float, y10: float) -> int:
    spread = y10 - y2
    if spread < CALIBRATION["yield_curve"]["deep_inversion"]:
        return 2
    if spread < CALIBRATION["yield_curve"]["inversion"]:
        return 1
    return 0


def build_constraint_scores(data: dict[str, float]) -> dict[str, int]:
    return {
        "policy": score_policy_constraint(float(data["core_pce"]), float(data["unemployment"])),
        "growth": score_growth_constraint(float(data["unemployment"])),
        "financial": score_financial_constraint(float(data["hy_spread"])),
        "curve": score_yield_curve(float(data["2y"]), float(data["10y"])),
    }
