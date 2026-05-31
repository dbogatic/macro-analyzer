"""
Calibration thresholds — hybrid empirical + policy-anchored + market-convention methodology.

Derivation
----------
Data range   : 1996-01-01 to present
COVID window : 2020-02-01 - 2021-12-31 excluded (exogenous shock,
               unprecedented policy response, non-repeatable conditions)
Recessions   : 2001 dot-com/9-11, 2007-09 GFC (NBER dates via USREC)
Method       : 25th percentile of 12-month pre-recession values = moderate
               75th percentile of 12-month pre-recession values = high

Per-series decisions
--------------------
unemployment : Empirical. Pre-recession distribution (4.0 / 4.6).

core_pce     : POLICY-ANCHORED. Empirical values (1.87 / 2.19) rejected
               because inflation was not the causal driver of either the
               2001 or 2008 recessions. Thresholds anchored to Fed
               dual-mandate tolerance bands and 2-3% historical norm.

hy_spread    : Empirical. Pre-recession distribution (3.89 / 7.0).

yield_curve  : Empirical. Flattening begins well before inversion.
               inversion = 0.52 (warning zone), deep = -0.17.

vix          : Market convention. VIX < 20 = normal; 20-30 = elevated
               stress; > 30 = crisis/fear. These are globally accepted
               thresholds used by risk managers and central banks alike.
               Not empirically re-derived — the convention IS the signal.

oil          : Judgment-anchored to supply constraint levels.
               $75 = level above which energy costs begin constraining
               corporate margins and consumer spending in a modern economy.
               $95 = level historically associated with demand destruction
               and stagflationary pressure. Both thresholds reflect
               post-2005 oil market structure (shale breakeven dynamics).

gold_yoy     : Judgment-anchored. Gold YoY > 15% signals elevated
               safe-haven demand — institutional risk-off behavior.
               > 30% signals crisis-level flight to safety (rare; seen
               in 2008, 2020). Not empirically calibrated because gold
               responds to too many unrelated factors (dollar, real rates,
               geopolitics) to derive clean recession-linked thresholds.

Re-run scripts/calibrate_thresholds.py to regenerate empirical values.
"""

CALIBRATION = {
    "unemployment": {
        "moderate": 4.0,   # empirical: 25th pct pre-recession (2001, 2008)
        "high":     4.6,   # empirical: 75th pct pre-recession (2001, 2008)
    },
    "core_pce": {
        "moderate": 2.5,   # policy-anchored: persistently above Fed 2% target
        "high":     3.0,   # policy-anchored: above 3%, Fed flexibility materially constrained
    },
    "hy_spread": {
        "moderate": 3.89,  # empirical: 25th pct pre-recession (2001, 2008)
        "high":     7.0,   # empirical: 75th pct pre-recession (GFC stress level)
    },
    "yield_curve": {
        "inversion":      0.52,   # empirical: curve flattening into warning zone
        "deep_inversion": -0.17,  # empirical: spread clearly negative
    },
    "vix": {
        "moderate": 20,    # market convention: elevated fear threshold
        "high":     30,    # market convention: crisis/fear threshold
    },
    "oil": {
        "moderate": 75,    # judgment: energy costs begin constraining growth
        "severe":   95,    # judgment: demand destruction / stagflationary pressure
    },
    # gold_yoy thresholds defined but not active.
    # Gold spot price unavailable via free FRED API (GOLDAMGBD228NLBM discontinued).
    # institutional fragility score is hardcoded to 0 until an alternative is sourced.
    "gold_yoy": {
        "moderate": 15,    # judgment: elevated safe-haven demand
        "high":     30,    # judgment: crisis-level flight to safety
    },
    "probability_adjustments": {
        "constraint_high": 0.10,
        "fragility_high":  0.10,
        "momentum_shift":  0.05,
        "trigger_shift":   0.03,
    },
}
