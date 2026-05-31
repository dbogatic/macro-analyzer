"""
Empirical threshold calibration script.

Derives constraint thresholds and scenario probability priors from FRED data.

Methodology
-----------
- Data range    : 1996-01-01 to present
- Frequency     : Monthly (last observation per month)
- COVID window  : 2020-02-01 - 2021-12-31 excluded from all calculations.
                  Rationale: exogenous supply shock + unprecedented policy
                  response ($5T stimulus, ZLB in two weeks, unlimited QE).
                  Including it would calibrate thresholds only relevant if
                  COVID-scale stimulus is repeated.
- Recessions    : NBER dates via USREC series (1 = recession, 0 = expansion)
- Included      : 2001 dot-com/9-11, 2007-09 GFC
- Excluded      : 2020 COVID (falls in excluded window)
- Pre-recession : 12-month lead window before each recession start
- Moderate      : 25th percentile of pre-recession values
                  (earliest point where pre-recession distribution diverges
                  from normal-period distribution)
- High          : 75th percentile of pre-recession values
                  (clearly elevated stress territory)

Usage
-----
    python -m scripts.calibrate_thresholds            # print report only
    python -m scripts.calibrate_thresholds --write    # also update calibration.py

Limitations
-----------
- Only two full recession cycles available (2001, 2008). Small sample.
- Structural changes post-2008 (QE, ZLB, fiscal dominance) may affect
  forward validity of historically derived thresholds.
- Re-run as new recession cycles accumulate.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Allow running as `python -m scripts.calibrate_thresholds` from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.loaders.fred_loader import load_series_range

# -- Constants ----------------------------------------------------------------─

START_DATE = "1996-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")
COVID_START = "2020-02-01"
COVID_END = "2021-12-31"
PRE_RECESSION_MONTHS = 12

SERIES_IDS = {
    "usrec":    "USREC",
    "core_pce": "PCEPILFE",
    "unemployment": "UNRATE",
    "hy_spread": "BAMLH0A0HYM2",
    "10y":      "DGS10",
    "2y":       "DGS2",
}

# -- Data loading --------------------------------------------------------------

def load_data() -> pd.DataFrame:
    print("Loading FRED data...")
    frames: dict[str, pd.Series] = {}
    for label, series_id in SERIES_IDS.items():
        print(f"  {label} ({series_id})")
        s = load_series_range(series_id, START_DATE, END_DATE)
        s.index = pd.to_datetime(s.index)
        frames[label] = s

    df = pd.DataFrame(frames)
    df = df.resample("MS").last()  # month-start, last obs per month

    # Derived series
    df["core_pce_yoy"] = df["core_pce"].ffill().pct_change(12, fill_method=None) * 100
    df["yield_curve"]  = df["10y"] - df["2y"]

    # Exclude COVID window
    covid_mask = (df.index >= COVID_START) & (df.index <= COVID_END)
    excluded = covid_mask.sum()
    df = df[~covid_mask]
    print(f"\nCOVID window excluded: {COVID_START} - {COVID_END} ({excluded} months removed)")

    return df

# -- Recession identification --------------------------------------------------

def get_recession_starts(usrec: pd.Series) -> list[pd.Timestamp]:
    """Return dates where USREC transitions 0 to 1 (recession onset)."""
    transitions = usrec.diff()
    starts = usrec[transitions == 1].index.tolist()
    return starts


def build_pre_recession_mask(df: pd.DataFrame, starts: list[pd.Timestamp]) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for start in starts:
        window_start = start - pd.DateOffset(months=PRE_RECESSION_MONTHS)
        window_end   = start - pd.DateOffset(months=1)
        mask |= (df.index >= window_start) & (df.index <= window_end)
    return mask

# -- Threshold derivation ------------------------------------------------------

def pct(values: pd.Series, p: int) -> float:
    return round(float(np.percentile(values.dropna(), p)), 2)


def derive_thresholds(df: pd.DataFrame, pre_mask: pd.Series) -> dict:
    pre    = df[pre_mask]
    normal = df[~pre_mask & (df["usrec"] == 0)]

    return {
        "core_pce": {
            # Higher is worse — pre-recession inflation elevated
            "moderate":           pct(pre["core_pce_yoy"], 25),
            "high":               pct(pre["core_pce_yoy"], 75),
            "_pre_recession_mean": round(float(pre["core_pce_yoy"].dropna().mean()), 2),
            "_normal_mean":        round(float(normal["core_pce_yoy"].dropna().mean()), 2),
        },
        "unemployment": {
            # Higher is worse — labour deterioration
            "moderate":           pct(pre["unemployment"], 25),
            "high":               pct(pre["unemployment"], 75),
            "_pre_recession_mean": round(float(pre["unemployment"].dropna().mean()), 2),
            "_normal_mean":        round(float(normal["unemployment"].dropna().mean()), 2),
        },
        "hy_spread": {
            # Higher is worse — financial stress
            "moderate":           pct(pre["hy_spread"], 25),
            "high":               pct(pre["hy_spread"], 75),
            "_pre_recession_mean": round(float(pre["hy_spread"].dropna().mean()), 2),
            "_normal_mean":        round(float(normal["hy_spread"].dropna().mean()), 2),
        },
        "yield_curve": {
            # Lower is worse — inversion precedes recession
            # threshold used as: spread < threshold to fires
            # inversion      = 75th pct of pre-recession (flattening early warning)
            # deep_inversion = 25th pct of pre-recession (severe inversion)
            "inversion":           pct(pre["yield_curve"], 75),
            "deep_inversion":      pct(pre["yield_curve"], 25),
            "_pre_recession_mean": round(float(pre["yield_curve"].dropna().mean()), 2),
            "_normal_mean":        round(float(normal["yield_curve"].dropna().mean()), 2),
        },
    }

# -- Probability priors --------------------------------------------------------

def derive_priors(df: pd.DataFrame) -> dict:
    total             = len(df)
    recession_months  = int(df["usrec"].sum())
    expansion_months  = total - recession_months

    # Historical recession base rate to informs downside prior
    recession_rate    = round(recession_months / total, 3)

    # Within expansion, use HY spread to split base vs upside
    # Stress expansion = HY spread in top quartile of expansion values
    exp = df[df["usrec"] == 0]
    hy_75 = float(exp["hy_spread"].quantile(0.75))
    stress_expansion  = int((exp["hy_spread"] >= hy_75).sum())
    smooth_expansion  = expansion_months - stress_expansion

    return {
        "total_months":      total,
        "recession_months":  recession_months,
        "expansion_months":  expansion_months,
        "recession_rate":    recession_rate,
        "smooth_expansion":  smooth_expansion,
        "stress_expansion":  stress_expansion,
        "hy_stress_threshold": round(hy_75, 2),
        # Suggested priors (normalised to 1.0)
        "suggested_downside": recession_rate,
        "suggested_base":     round(smooth_expansion / total, 3),
        "suggested_upside":   round(stress_expansion / total, 3),
    }

# -- Report --------------------------------------------------------------------

def print_report(
    thresholds: dict,
    priors: dict,
    recession_starts: list[pd.Timestamp],
) -> None:
    sep = "=" * 70

    print(f"\n{sep}")
    print("  EMPIRICAL CALIBRATION REPORT")
    print(f"  Data: {START_DATE} to {END_DATE}")
    print(f"  COVID excluded: {COVID_START} - {COVID_END}")
    print(f"  Pre-recession window: {PRE_RECESSION_MONTHS} months")
    print(f"  Recessions in sample: {[d.strftime('%Y-%m') for d in recession_starts]}")
    print(sep)

    print("\n-- CONSTRAINT THRESHOLDS --\n")
    for series, vals in thresholds.items():
        print(f"  {series}:")
        for k, v in vals.items():
            label = k.lstrip("_")
            print(f"    {label:<22}: {v}")

    print("\n-- SCENARIO PROBABILITY PRIORS --\n")
    print(f"  Total months in sample : {priors['total_months']}")
    print(f"  Recession months        : {priors['recession_months']}  ({priors['recession_rate']*100:.1f}%)")
    print(f"  Expansion months        : {priors['expansion_months']}")
    print(f"  HY stress threshold     : {priors['hy_stress_threshold']} (75th pct of expansion HY spread)")
    print(f"  Stress expansion months : {priors['stress_expansion']}")
    print(f"  Smooth expansion months : {priors['smooth_expansion']}")
    print()
    print(f"  Suggested downside prior : {priors['suggested_downside']*100:.1f}%  (historical recession rate)")
    print(f"  Suggested base prior     : {priors['suggested_base']*100:.1f}%  (smooth expansion frequency)")
    print(f"  Suggested upside prior   : {priors['suggested_upside']*100:.1f}%  (stress expansion frequency)")
    print()
    print("  NOTE: Current model uses 45/30/25 (base/upside/downside).")
    print("  The empirical recession rate is lower than 25% because NBER recessions")
    print("  are short relative to the full cycle. Review before updating priors.")

    print(f"\n-- RECOMMENDED calibration.py VALUES --\n")
    t = thresholds
    print('CALIBRATION = {')
    print(f'    "unemployment": {{"moderate": {t["unemployment"]["moderate"]}, "high": {t["unemployment"]["high"]}}},')
    print(f'    "core_pce":     {{"moderate": {t["core_pce"]["moderate"]},     "high": {t["core_pce"]["high"]}}},')
    print(f'    "hy_spread":    {{"moderate": {t["hy_spread"]["moderate"]},    "high": {t["hy_spread"]["high"]}}},')
    print(f'    "yield_curve":  {{"inversion": {t["yield_curve"]["inversion"]}, "deep_inversion": {t["yield_curve"]["deep_inversion"]}}},')
    print('    "probability_adjustments": { ... },  # unchanged')
    print('}')
    print(sep)

# -- Write calibration.py ------------------------------------------------------

def write_calibration(thresholds: dict) -> None:
    t = thresholds
    calibration_path = Path(__file__).resolve().parents[1] / "config" / "calibration.py"

    content = f'''\
"""
Empirically derived calibration thresholds.

Methodology
-----------
- Data range    : {START_DATE} - {END_DATE}
- COVID window  : {COVID_START} - {COVID_END} excluded
- Recessions    : 2001 (dot-com), 2007-09 (GFC)
- Moderate      : 25th percentile of 12-month pre-recession values
- High          : 75th percentile of 12-month pre-recession values
- Yield curve   : inversion = 75th pct pre-recession spread (flattening warning)
                  deep_inversion = 25th pct pre-recession spread (severe)

Re-run scripts/calibrate_thresholds.py --write to update.
"""

CALIBRATION = {{
    "unemployment": {{"moderate": {t["unemployment"]["moderate"]}, "high": {t["unemployment"]["high"]}}},
    "core_pce":     {{"moderate": {t["core_pce"]["moderate"]},     "high": {t["core_pce"]["high"]}}},
    "hy_spread":    {{"moderate": {t["hy_spread"]["moderate"]},    "high": {t["hy_spread"]["high"]}}},
    "yield_curve":  {{"inversion": {t["yield_curve"]["inversion"]}, "deep_inversion": {t["yield_curve"]["deep_inversion"]}}},
    "probability_adjustments": {{
        "constraint_high": 0.10,
        "fragility_high":  0.10,
        "momentum_shift":  0.05,
        "trigger_shift":   0.03,
    }},
}}
'''

    calibration_path.write_text(content)
    print(f"\nWrote updated thresholds to {calibration_path}")

# -- Entry point --------------------------------------------------------------─

def main() -> None:
    parser = argparse.ArgumentParser(description="Empirically calibrate macro thresholds from FRED data.")
    parser.add_argument("--write", action="store_true", help="Write derived thresholds to config/calibration.py")
    args = parser.parse_args()

    df = load_data()

    recession_starts = get_recession_starts(df["usrec"])
    print(f"\nRecession starts found in clean sample: {[d.strftime('%Y-%m') for d in recession_starts]}")

    pre_mask = build_pre_recession_mask(df, recession_starts)
    print(f"Pre-recession months in sample: {pre_mask.sum()}")

    thresholds = derive_thresholds(df, pre_mask)
    priors     = derive_priors(df)

    print_report(thresholds, priors, recession_starts)

    if args.write:
        confirm = input("\nWrite these thresholds to config/calibration.py? [y/N] ").strip().lower()
        if confirm == "y":
            write_calibration(thresholds)
        else:
            print("Aborted. No files written.")
    else:
        print("\nRun with --write to update config/calibration.py.")


if __name__ == "__main__":
    main()
