from __future__ import annotations

from config.calibration import CALIBRATION


def score_fragility(data: dict) -> dict[str, int]:
    hy       = float(data["hy_spread"])
    spread   = float(data["10y"]) - float(data["2y"])
    vix      = float(data.get("vix", 20))    # default 20 = normal if unavailable
    oil      = float(data.get("oil", 70))    # default $70 = below moderate threshold
    gold_yoy = float(data.get("gold", 0))    # GLD ETF YoY %, 0 = neutral if unavailable

    vix_mod   = CALIBRATION["vix"]["moderate"]
    vix_high  = CALIBRATION["vix"]["high"]
    oil_mod   = CALIBRATION["oil"]["moderate"]
    oil_sev   = CALIBRATION["oil"]["severe"]
    gold_mod  = CALIBRATION["gold_yoy"]["moderate"]
    gold_high = CALIBRATION["gold_yoy"]["high"]
    ds_mod    = CALIBRATION["debt_service"]["moderate"]
    ds_high   = CALIBRATION["debt_service"]["high"]

    # Leverage: driven by household debt service ratio (TDSP).
    # Default is 0 when data is unavailable — honest for a deleveraging
    # environment. The old hardcoded 1 was correct on average but wrong
    # at cycle extremes (post-GFC deleveraging 2012-2015).
    debt_service = data.get("debt_service")
    if debt_service is not None:
        ds = float(debt_service)
        leverage_score = 2 if ds > ds_high else 1 if ds > ds_mod else 0
    else:
        leverage_score = 0

    scores = {
        "leverage": leverage_score,

        # Liquidity: driven by both HY spread (credit market stress)
        # and VIX (market fear). Takes the worse of the two signals.
        "liquidity": max(
            2 if hy > 6         else 1 if hy > 4        else 0,
            2 if vix > vix_high else 1 if vix > vix_mod else 0,
        ),

        # Energy dependency: driven by WTI oil price level.
        # High oil raises input costs and constrains growth.
        "energy_dependency": 2 if oil > oil_sev else 1 if oil > oil_mod else 0,

        # Correlation: yield curve inversion signals correlation breakdown
        # across asset classes (bonds stop hedging equities).
        "correlation": 1 if spread < 0 else 0,

        # Institutional: GLD ETF YoY % via Stooq. Rising gold signals risk-off
        # flight to safety and institutional stress (2008, 2020 precedent).
        "institutional": 2 if gold_yoy > gold_high else 1 if gold_yoy > gold_mod else 0,
    }
    return scores
