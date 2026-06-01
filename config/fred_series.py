FRED_SERIES = {
    # Macro fundamentals — required, analysis stops if these fail
    "core_pce":     "PCEPILFE",         # Core PCE price index — converted to YoY %
    "cpi":          "CPIAUCSL",         # CPI — converted to YoY %
    "unemployment": "UNRATE",           # Unemployment rate %
    "fed_funds":    "FEDFUNDS",         # Fed funds rate %
    "10y":          "DGS10",            # 10-year Treasury yield %
    "2y":           "DGS2",             # 2-year Treasury yield %
    "hy_spread":    "BAMLH0A0HYM2",     # High-yield credit spread %
}

# Market signals — optional, analysis continues if these fail
MARKET_SIGNALS = {
    "vix":            "VIXCLS",      # CBOE VIX — market fear gauge
    "oil":            "DCOILWTICO",  # WTI crude oil price (USD/barrel)
    "jobless_claims": "ICSA",        # Initial jobless claims (weekly) — leading labor signal
    "debt_service":   "TDSP",        # Household debt service ratio (quarterly) — leverage proxy
    # Gold: FRED series discontinued. Loaded via Stooq (GLD ETF) in app.py.
}
