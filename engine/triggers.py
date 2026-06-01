from __future__ import annotations

from dataclasses import asdict, dataclass

from config.calibration import CALIBRATION


@dataclass
class Trigger:
    name: str
    value: float | str
    threshold: str
    direction: str
    scenario_up: str
    scenario_down: str
    dimension: str
    message: str
    fired: bool


def unemployment_trigger(current_unemployment: float) -> Trigger:
    fired = current_unemployment >= 4.5
    return Trigger(
        "Unemployment Deterioration",
        current_unemployment,
        ">= 4.5",
        "up",
        "Downside Break",
        "Stabilization / Policy Relief",
        "Growth / Labor",
        "Labor market deterioration raises downside scenario probability.",
        fired,
    )


def core_pce_trigger(core_pce: float) -> Trigger:
    threshold = CALIBRATION["core_pce"]["high"]
    fired = core_pce >= threshold
    return Trigger(
        "Core PCE Persistence",
        core_pce,
        f">= {threshold}",
        "up",
        "Controlled Deceleration",
        "Stabilization / Policy Relief",
        "Policy Constraint",
        "Sticky inflation limits policy flexibility and reduces upside relief odds.",
        fired,
    )


def hy_spread_trigger(hy_spread: float) -> Trigger:
    fired = hy_spread >= 5.0
    return Trigger(
        "Credit Stress Widening",
        hy_spread,
        ">= 5.0",
        "up",
        "Downside Break",
        "Controlled Deceleration",
        "Financial Stress",
        "Wider high-yield spreads raise downside risk.",
        fired,
    )


def yield_curve_trigger(y2: float, y10: float) -> Trigger:
    spread = y10 - y2
    fired = spread < 0
    return Trigger(
        "Yield Curve Inversion",
        round(spread, 2),
        "< 0",
        "down",
        "Downside Break",
        "Stabilization / Policy Relief",
        "Rates / Macro Signal",
        "An inverted curve reinforces slowdown and downside-risk signals.",
        fired,
    )


def vix_trigger(vix: float) -> Trigger:
    threshold = CALIBRATION["vix"]["high"]  # 30 = crisis
    fired = vix >= threshold
    return Trigger(
        "VIX Spike",
        round(vix, 1),
        f">= {threshold}",
        "up",
        "Downside Break",
        "Stabilization / Policy Relief",
        "Market Fear",
        "VIX at crisis level signals broad market fear and elevated tail risk.",
        fired,
    )


def oil_trigger(oil: float) -> Trigger:
    threshold = CALIBRATION["oil"]["severe"]  # $95
    fired = oil >= threshold
    return Trigger(
        "Oil Price Shock",
        round(oil, 1),
        f">= ${threshold}",
        "up",
        "Downside Break",
        "Controlled Deceleration",
        "Energy / Supply",
        "Severe oil price level signals stagflationary pressure and demand destruction risk.",
        fired,
    )


def gold_trigger(gold_yoy: float) -> Trigger:
    threshold = CALIBRATION["gold_yoy"]["moderate"]  # 15%
    fired = gold_yoy >= threshold
    return Trigger(
        "Gold Safe-Haven Demand",
        round(gold_yoy, 1),
        f">= {threshold}%",
        "up",
        "Downside Break",
        "Controlled Deceleration",
        "Institutional / Risk-Off",
        "Elevated gold YoY return signals institutional flight to safety.",
        fired,
    )


def evaluate_triggers(data: dict[str, float]) -> list[Trigger]:
    triggers = [
        unemployment_trigger(float(data["unemployment"])),
        core_pce_trigger(float(data["core_pce"])),
        hy_spread_trigger(float(data["hy_spread"])),
        yield_curve_trigger(float(data["2y"]), float(data["10y"])),
    ]
    # Market signals — optional, added only when data is available
    if data.get("vix") is not None:
        triggers.append(vix_trigger(float(data["vix"])))
    if data.get("oil") is not None:
        triggers.append(oil_trigger(float(data["oil"])))
    if data.get("gold") is not None:
        triggers.append(gold_trigger(float(data["gold"])))
    return triggers


# Maps trigger dimension to the fragility score key it overlaps with.
# When a signal is already maxed in fragility (score=2), the trigger fires
# at half-strength to prevent the same signal from creating outsized
# probability swings through double-counting.
_TRIGGER_FRAGILITY_MAP: dict[str, str] = {
    "Market Fear":              "liquidity",
    "Financial Stress":         "liquidity",
    "Energy / Supply":          "energy_dependency",
    "Institutional / Risk-Off": "institutional",
}


def _dampening_factor(trigger: Trigger, fragility_scores: dict | None) -> float:
    if not fragility_scores:
        return 1.0
    frag_key = _TRIGGER_FRAGILITY_MAP.get(trigger.dimension)
    if frag_key and fragility_scores.get(frag_key, 0) >= 2:
        return 0.5
    return 1.0


def apply_trigger_adjustments(
    scenarios: list[dict],
    triggers: list[Trigger],
    fragility_scores: dict | None = None,
) -> list[dict]:
    fired = [t for t in triggers if t.fired]
    scenario_map = {s["name"]: dict(s) for s in scenarios}

    for trigger in fired:
        factor = _dampening_factor(trigger, fragility_scores)
        if trigger.scenario_up in scenario_map:
            low, high = scenario_map[trigger.scenario_up]["probability"]
            scenario_map[trigger.scenario_up]["probability"] = (
                low  + 0.02 * factor,
                high + 0.03 * factor,
            )
        if trigger.scenario_down in scenario_map:
            low, high = scenario_map[trigger.scenario_down]["probability"]
            scenario_map[trigger.scenario_down]["probability"] = (
                max(0.0, low  - 0.02 * factor),
                max(0.0, high - 0.03 * factor),
            )

    return list(scenario_map.values())


def triggers_to_dicts(triggers: list[Trigger]) -> list[dict]:
    return [asdict(t) for t in triggers]
