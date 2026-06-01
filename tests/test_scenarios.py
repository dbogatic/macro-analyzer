from engine.scenario_probabilities import assign_probabilities
from engine.scenarios import build_scenarios


def test_scenarios_three_paths():
    scenarios = build_scenarios({
        "constraint_score": 5,
        "fragility_score": 4,
        "momentum": "Stable",
        "regime": "Stress",
    })
    assert len(scenarios) == 3


# --- Regime-conditional priors ---

def test_break_regime_downside_dominates_before_adjustments():
    # Break prior sets downside to 0.50 before any score adjustments.
    # Even with zero constraint/fragility/momentum the downside should
    # remain the largest single scenario after normalization.
    probs = assign_probabilities(0, 0, "Stable", regime="Break")
    low, high = probs["downside"]
    assert (low + high) / 2 > 0.40, "Break regime downside mid should exceed 40%"


def test_stabilization_regime_upside_exceeds_stress():
    stable = assign_probabilities(0, 0, "Stable", regime="Stabilization")
    stress = assign_probabilities(0, 0, "Stable", regime="Stress")
    stable_up_mid = sum(stable["upside"]) / 2
    stress_up_mid = sum(stress["upside"]) / 2
    assert stable_up_mid > stress_up_mid, "Stabilization should produce higher upside than Stress"


def test_break_downside_greater_than_stabilization_downside():
    brk = assign_probabilities(0, 0, "Stable", regime="Break")
    stab = assign_probabilities(0, 0, "Stable", regime="Stabilization")
    assert sum(brk["downside"]) / 2 > sum(stab["downside"]) / 2


# --- Cross-module interaction terms ---

def test_policy_financial_interaction_raises_downside():
    without = assign_probabilities(2, 2, "Stable", regime="Stress", constraint_scores=None)
    with_interaction = assign_probabilities(
        2, 2, "Stable", regime="Stress",
        constraint_scores={"policy": 1, "financial": 1, "growth": 0, "curve": 0},
    )
    assert sum(with_interaction["downside"]) / 2 > sum(without["downside"]) / 2


def test_growth_financial_interaction_raises_downside():
    without = assign_probabilities(2, 2, "Stable", regime="Stress", constraint_scores=None)
    with_interaction = assign_probabilities(
        2, 2, "Stable", regime="Stress",
        constraint_scores={"policy": 0, "financial": 1, "growth": 1, "curve": 0},
    )
    assert sum(with_interaction["downside"]) / 2 > sum(without["downside"]) / 2


# --- Financial trend signals ---

def test_widening_hy_raises_downside():
    flat   = assign_probabilities(3, 3, "Stable", regime="Stress", financial_trend=None)
    widens = assign_probabilities(3, 3, "Stable", regime="Stress",
                                  financial_trend={"hy_trend": "Widening", "curve_trend": None})
    assert sum(widens["downside"]) / 2 > sum(flat["downside"]) / 2


def test_inverting_curve_raises_downside():
    flat     = assign_probabilities(3, 3, "Stable", regime="Stress", financial_trend=None)
    inverting = assign_probabilities(3, 3, "Stable", regime="Stress",
                                     financial_trend={"hy_trend": None, "curve_trend": "Inverting"})
    assert sum(inverting["downside"]) / 2 > sum(flat["downside"]) / 2


def test_tightening_hy_raises_upside():
    flat     = assign_probabilities(3, 3, "Stable", regime="Stress", financial_trend=None)
    tightens = assign_probabilities(3, 3, "Stable", regime="Stress",
                                    financial_trend={"hy_trend": "Tightening", "curve_trend": None})
    assert sum(tightens["upside"]) / 2 > sum(flat["upside"]) / 2


# --- Trigger dampening ---

def test_trigger_dampened_when_fragility_maxed():
    from engine.triggers import _dampening_factor, Trigger
    trigger = Trigger(
        name="VIX Spike", value=35.0, threshold=">= 30", direction="up",
        scenario_up="Downside Break", scenario_down="Stabilization / Policy Relief",
        dimension="Market Fear", message="VIX crisis", fired=True,
    )
    full = _dampening_factor(trigger, fragility_scores=None)
    dampened = _dampening_factor(trigger, fragility_scores={"liquidity": 2})
    assert full == 1.0
    assert dampened == 0.5


def test_trigger_not_dampened_when_fragility_moderate():
    from engine.triggers import _dampening_factor, Trigger
    trigger = Trigger(
        name="VIX Spike", value=25.0, threshold=">= 30", direction="up",
        scenario_up="Downside Break", scenario_down="Stabilization / Policy Relief",
        dimension="Market Fear", message="VIX elevated", fired=True,
    )
    factor = _dampening_factor(trigger, fragility_scores={"liquidity": 1})
    assert factor == 1.0
