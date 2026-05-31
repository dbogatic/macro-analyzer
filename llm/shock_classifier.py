"""
LLM-based geopolitical/energy shock classifier.

Reads recent news headlines and classifies the current energy/geopolitical
risk level as None, Moderate, or Severe. The result is used to pre-fill
the manual override in the sidebar — the user reviews and confirms before
the analysis runs.

Design decisions
----------------
- Classification is a separate, lightweight LLM call (not part of the main
  report). It uses a structured prompt and expects JSON output only, making
  it fast, cheap, and deterministic enough to be reliable.
- The classifier SUGGESTS a level — it does not auto-apply it. The user
  always has final say. This keeps the model auditable: every weight change
  is a conscious human decision, not a black box.
- If OpenAI key is not set or the call fails, returns None so the sidebar
  falls back to manual selection without error.
"""

from __future__ import annotations

import json

from openai import OpenAI

from config.settings import settings

CLASSIFIER_PROMPT = """You are a macro risk analyst. Review the following recent news headlines and quantitative market signals, then classify the current energy/geopolitical risk level for a global macro model.

Definitions:
- None: No significant energy or geopolitical disruption. Normal market conditions.
- Moderate: Elevated tension or uncertainty not yet causing confirmed supply disruption.
  Examples: tariff threats, diplomatic standoffs, oil price volatility without confirmed supply loss,
  military buildup without active strikes on infrastructure.
- Severe: Active disruption to energy supply chains or financial systems with confirmed real-world impact.
  Examples: active war involving major oil producer (Iran, Russia, Saudi Arabia), Strait of Hormuz
  closure or credible threat to it, Red Sea shipping disruptions forcing rerouting, major oil
  infrastructure struck, broad sanctions cutting off significant oil/gas supply, pipeline shutdown.
  If Hormuz is mentioned as closed, blocked, or under attack -> always Severe.
  If Iran is in active military conflict -> always Severe.
  If the Oil Price Shock trigger has fired (oil above severe threshold) -> at minimum Moderate, likely Severe.

Be explicit: if the headlines confirm active conflict or supply chokepoint disruption, classify as Severe
even if some headlines are unrelated. One confirmed Severe signal overrides ambient Moderate noise.
Quantitative signals that have fired their thresholds should be treated as corroborating evidence —
high oil prices reflect supply stress even when headlines use cautious language.

Headlines:
{headlines}
{quant_context}
Respond with JSON only, no other text:
{{"level": "None", "reason": "one sentence explanation"}}"""


def _build_quant_context(quant_signals: dict) -> str:
    """Format quantitative market signals for the classifier prompt."""
    from config.calibration import CALIBRATION
    lines = []
    oil = quant_signals.get("oil")
    if oil is not None:
        oil = float(oil)
        sev = CALIBRATION["oil"]["severe"]
        mod = CALIBRATION["oil"]["moderate"]
        status = "SEVERE THRESHOLD FIRED" if oil >= sev else "moderate threshold fired" if oil >= mod else "below thresholds"
        lines.append(f"- WTI Oil: ${oil:.0f}/bbl — {status} (moderate=${mod}, severe=${sev})")
    vix = quant_signals.get("vix")
    if vix is not None:
        vix = float(vix)
        high = CALIBRATION["vix"]["high"]
        status = "CRISIS THRESHOLD FIRED" if vix >= high else "below crisis threshold"
        lines.append(f"- VIX: {vix:.1f} — {status} (crisis={high})")
    gold = quant_signals.get("gold")
    if gold is not None:
        gold = float(gold)
        high = CALIBRATION["gold_yoy"]["high"]
        mod  = CALIBRATION["gold_yoy"]["moderate"]
        status = "CRISIS THRESHOLD FIRED" if gold >= high else "elevated threshold fired" if gold >= mod else "below thresholds"
        lines.append(f"- Gold YoY: {gold:.1f}% — {status} (elevated={mod}%, crisis={high}%)")
    if not lines:
        return ""
    return "\nQuantitative signals:\n" + "\n".join(lines) + "\n"


def classify_shock(headlines: list[dict], quant_signals: dict | None = None) -> dict | None:
    """
    Classify energy/geopolitical shock level from news headlines and quantitative signals.

    quant_signals: dict of market data (oil, vix, gold) from the current run.
    When provided, the classifier can see which thresholds have fired — e.g. oil
    at $114 firing the severe trigger is corroborating evidence even if headlines
    use cautious language about "no confirmed supply interruptions".

    Returns dict with keys: level (None/Moderate/Severe), reason (str).
    Returns None if classification fails or API key is not set.
    """
    if not settings.openai_api_key or not headlines:
        return None

    headlines_text = "\n".join(
        f"- [{h['source']}] {h['title']} ({h['published']})"
        for h in headlines
    )
    quant_context = _build_quant_context(quant_signals) if quant_signals else ""

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": CLASSIFIER_PROMPT.format(
                headlines=headlines_text, quant_context=quant_context
            )}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        if result.get("level") in ("None", "Moderate", "Severe"):
            return result
        return None
    except Exception as e:
        raise RuntimeError(f"Shock classifier failed: {e}") from e
