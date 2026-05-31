from __future__ import annotations

import streamlit as st


def render_dashboard(data: dict, classification: str, constraint_total: float, fragility_total: float) -> None:
    st.subheader("Macro Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    unemp = data.get("unemployment")
    c1.metric("Unemployment", f"{unemp:.1f}%" if isinstance(unemp, (int, float)) else "n/a")
    pce = data.get("core_pce")
    c2.metric("Core PCE", f"{pce:.2f}%" if isinstance(pce, (int, float)) else "n/a")
    fed = data.get("fed_funds")
    c3.metric("Fed Funds", f"{fed:.2f}%" if isinstance(fed, (int, float)) else "n/a")
    spread = None
    if isinstance(data.get("10y"), (int, float)) and isinstance(data.get("2y"), (int, float)):
        spread = round(float(data["10y"]) - float(data["2y"]), 2)
    c4.metric("10Y-2Y", spread if spread is not None else "n/a")

    if classification == "Smooth":
        st.success(f"🟢 {classification} | Constraint {constraint_total}/10 | Fragility {fragility_total}/10")
    elif classification == "Turbulence":
        st.warning(f"🟡 {classification} | Constraint {constraint_total}/10 | Fragility {fragility_total}/10")
    else:
        st.error(f"🔴 {classification} | Constraint {constraint_total}/10 | Fragility {fragility_total}/10")

    # Market signals panel
    st.subheader("Market Signals")
    m1, m2, m3 = st.columns(3)

    vix = data.get("vix")
    m1.metric(
        "VIX",
        f"{vix:.1f}" if isinstance(vix, (int, float)) else "n/a",
        help="CBOE Volatility Index. < 20 = normal | 20-30 = elevated fear | > 30 = crisis"
    )

    oil = data.get("oil")
    m2.metric(
        "WTI Oil ($/bbl)",
        f"${oil:.1f}" if isinstance(oil, (int, float)) else "n/a",
        help="WTI crude oil price. > $75 = moderate energy pressure | > $95 = severe"
    )

    gold_yoy   = data.get("gold")
    gold_price = data.get("gold_price")
    price_str  = f"~${gold_price:,.0f}/oz" if isinstance(gold_price, (int, float)) else ""
    m3.metric(
        "Gold (spot approx.)",
        price_str if price_str else "n/a",
        delta=f"{gold_yoy:.1f}% YoY" if isinstance(gold_yoy, (int, float)) else None,
        help="Approximate gold spot price (GLD ETF × 10). Delta = YoY % change. > 15% YoY = elevated safe-haven demand | > 30% = crisis-level flight to safety"
    )
