# Macro Analyzer

Macro Analyzer is a Streamlit-based macro decision engine that converts macro data into scores, dynamic weights, disciplined scenarios, triggers, reports, history, and backtests.

---

## Disclaimer

**This tool is for internal decision support and structured analysis only. It does not constitute investment advice, financial planning recommendations, or any form of client-directed guidance.**

If you are a registered investment adviser or financial professional:

- All outputs from this tool must be reviewed in conjunction with your own professional judgment, current market data, and applicable regulatory requirements before being used in any client-facing context.
- The scenarios, probability estimates, and regime classifications produced here are illustrative frameworks — not forecasts, predictions, or guarantees of future results.
- Historical backtest results do not predict future performance. The model is calibrated on two recession cycles (2001, 2008) and has known structural limitations documented below.
- This tool does not account for individual client circumstances, risk tolerance, investment objectives, or tax situation.
- Use of this tool does not create any fiduciary, advisory, or legal obligation between the tool's outputs and any third party.

Nothing in this tool should be shared with clients as a basis for investment decisions without independent professional verification.

---

## What it does

- Pulls primary macro inputs from FRED
- Scores constraint pressure and fragility
- Classifies momentum, regime, and system state
- Adjusts current module weights versus a structural base model
- Generates 3 core scenarios with probability ranges
- Applies trigger-based scenario adjustments
- Normalizes and validates probabilities
- Generates a short or long narrative report with the OpenAI API
- Stores runs in SQLite for history tracking
- Supports historical backtesting and threshold calibration

## Intended use cases

### What this tool IS good for

- **Structured conversation preparation**: Translate macro data into a consistent, documented framework before client meetings
- **Regime identification**: Systematically determine whether the current environment looks more like expansion, stress, or crisis — with an auditable rationale
- **Scenario framing**: Force explicit probability assignment across 3 mutually exclusive paths rather than anchoring on a single forecast
- **Trigger monitoring**: Get alerted when VIX, oil, or other signals cross thresholds that historically precede stress regime shifts
- **Historical context**: Quickly compare current macro conditions against prior stress periods (GFC, 2022 tightening cycle)
- **Discipline enforcement**: The model's rule-based structure reduces recency bias and anchoring when conditions are ambiguous

### What this tool IS NOT

- A trading signal or market timing system
- A replacement for fundamental analysis or sector research
- A real-time risk monitor (FRED data is monthly and backward-looking by 4–8 weeks)
- A probability forecasting engine — the scenario percentages are structured priors, not statistical estimates
- A substitute for fiduciary judgment in client-specific situations
- Calibrated for or applicable to individual securities, funds, or portfolios

---

## Model architecture

The model is a **rule-based probabilistic regime classifier**. It takes macro data inputs, runs them through hard-threshold scoring functions, and outputs scenario probability distributions. Every output is traceable to a specific rule — there is no black box.

### Pipeline

```
FRED data → Constraint Scores → Fragility Scores
                                        ↓
                              Regime Classification
                                        ↓
                      Regime-Conditional Scenario Priors
                                        ↓
                     Score Adjustments + Interaction Terms
                                        ↓
                       Financial Trend Signal Adjustments
                                        ↓
                          Composite Momentum Adjustment
                                        ↓
                       Trigger Adjustments (dampened)
                                        ↓
                         Normalization + Validation
                                        ↓
                      Weight Reallocation (parallel path)
                                        ↓
                          LLM Narrative Report
```

### Constraint scoring

Measures how much the system is being pressed right now. Four dimensions, each scored 0–2:

| Dimension | Signal | Moderate (1) | High (2) |
|---|---|---|---|
| Policy | Core PCE + unemployment | PCE ≥ 2.5% | PCE ≥ 3.0% AND unemployment < 4.5% |
| Growth | Unemployment | ≥ 4.0% | ≥ 4.6% |
| Financial | HY credit spread | ≥ 3.89% | ≥ 7.0% |
| Yield Curve | 10y–2y spread | < 0.52% | < –0.17% |

Max total: 8. The Break regime threshold (≥7) requires multiple dimensions in simultaneous stress.

### Fragility scoring

Measures how brittle the system is if something goes wrong — distinct from current pressure. Six dimensions:

| Dimension | Signal | Moderate (1) | High (2) |
|---|---|---|---|
| Leverage | Household debt service ratio (TDSP) | > 10.5% | > 12.0% |
| Liquidity | HY spread or VIX (worst of two) | HY > 4% or VIX > 20 | HY > 6% or VIX > 30 |
| Energy Dependency | WTI oil price | > $75/bbl | > $95/bbl |
| Correlation Breakdown | Yield curve | Spread < 0 | — |
| Institutional | Gold YoY % | > 15% | > 30% |

Leverage is driven by the household debt service ratio (TDSP from FRED). When data is unavailable, leverage scores 0 — this is more honest than a hardcoded value, particularly in genuine deleveraging environments (e.g., 2012–2015 post-GFC).

### Regime classification

Three regimes determined by score totals and momentum:

| Regime | Classification | Condition |
|---|---|---|
| Break | Iceberg Risk | Constraint ≥ 7 OR Fragility ≥ 7 |
| Stabilization | Smooth | Both scores ≤ 4 AND momentum not Deteriorating |
| Stress | Turbulence | Everything else |

The asymmetry is intentional: it takes one bad dimension to reach Break, but both dimensions must be clean for Stabilization.

### Regime-conditional scenario priors

Scenario probabilities start from regime-dependent priors, not a fixed baseline. This allows the model to express that a clean expansion has real upside room, and that a Break regime already has elevated downside before any score adjustments are applied.

| Regime | Base (Deceleration) | Upside (Stabilization) | Downside (Break) |
|---|---|---|---|
| Stabilization | 50% | 35% | 15% |
| Stress | 45% | 30% | 25% |
| Break | 30% | 20% | 50% |

### Score adjustments (graduated)

Applied on top of regime priors:

| Score range | Effect |
|---|---|
| Constraint 3–4 | Downside +3%, Base –3% |
| Constraint 5–6 | Downside +7%, Base –5%, Upside –2% |
| Constraint ≥ 7 | Downside +12%, Base –7%, Upside –5% |
| Fragility 3–4 | Downside +3%, Base –3% |
| Fragility 5–6 | Downside +5%, Base –3%, Upside –2% |
| Fragility ≥ 7 | Downside +10%, Base –5%, Upside –5% |

### Cross-module interaction terms

Two modules stressed simultaneously is qualitatively more dangerous than the sum of their individual scores. These interaction terms capture feedback loops that additive scoring misses:

| Interaction | Effect | Rationale |
|---|---|---|
| Policy ≥ 1 AND Financial ≥ 1 | Downside +3%, Base –2%, Upside –1% | Trapped Fed + credit stress (2008 signature) |
| Growth ≥ 1 AND Financial ≥ 1 | Downside +2%, Base –2% | Labor deterioration + credit widening (recession confirmation) |

### Financial trend signals

The model reads level, not direction. A yield curve at –0.1% that was –0.5% (normalizing) is a different environment from one that was +0.5% and is now –0.1% (rapidly inverting). Trend signals correct this blind spot using 3-month deltas:

| Signal | Direction | Effect |
|---|---|---|
| HY spread | Widening > +0.5% | Downside +2% |
| HY spread | Tightening > –0.5% | Upside +2% |
| Yield curve | Inverting > –0.2% | Downside +2% |
| Yield curve | Normalizing > +0.2% | Upside +2% |

Trend signals are optional — the model runs without them if FRED is unavailable.

### Composite momentum

Momentum classification uses a composite of three signals. A single month's unemployment change is noisy; overriding Stable requires at least two signals to agree:

| Signal | Deteriorating | Improving |
|---|---|---|
| Single-month unemployment | Current > Previous | Current < Previous |
| 3-month unemployment trend | Rising > +0.1% | Falling > –0.1% |
| Initial jobless claims YoY (ICSA) | > +5% | < –5% |

**Rule:** Stable is overridden only when ≥ 2 signals agree on direction. Conflicting signals return Stable. This prevents a single noisy month from swinging the probability distribution.

Composite momentum effect: Deteriorating → Downside +5%, Base –5%. Improving → Upside +5%, Base –5%.

### Trigger adjustments

Seven explicit triggers apply fine-tuning adjustments after the score and trend layers. Each fires when a specific threshold is crossed and adjusts probabilities by ±0.02–0.03.

**Dampening:** Some signals feed into both the fragility score and a trigger (e.g., VIX into liquidity fragility and VIX Spike trigger). When the underlying signal is already maxed in fragility (score = 2), the trigger fires at half-strength to prevent double-counting from creating outsized swings in extreme stress.

| Trigger | Threshold | Dampened when |
|---|---|---|
| VIX Spike | VIX ≥ 30 | Liquidity fragility = 2 |
| Credit Stress Widening | HY spread ≥ 5.0% | Liquidity fragility = 2 |
| Oil Price Shock | Oil ≥ $95/bbl | Energy fragility = 2 |
| Gold Safe-Haven | Gold YoY ≥ 15% | Institutional fragility = 2 |

Triggers not subject to dampening (no fragility overlap): Unemployment Deterioration, Core PCE Persistence, Yield Curve Inversion.

### Structural base model

Base modules and default weights:

- Policy / Central Bank: 30%
- Growth / Macro: 25%
- Financial Conditions: 20%
- Energy / Geopolitical: 15%
- Political / Institutional: 10%

The base model is structural. Current weights change only when supported by rule-based logic tied to constraints, fragility, regime shifts, or active shocks.

## Data hierarchy

Primary scoring relies on official/public datasets from FRED. Market signals (VIX, WTI crude oil, gold) are pulled from FRED and Yahoo Finance to supplement the monthly macro data with daily market sentiment.

## Repo layout

```text
macro-analyzer/
├── app.py
├── config/
├── data/
├── engine/
├── llm/
├── ui/
├── exports/
├── backtesting/
├── scripts/
└── tests/
```

## Environment variables

Create a `.env` file in the project root:

```text
OPENAI_API_KEY=your_openai_key_here
FRED_API_KEY=your_fred_key_here
NEWSAPI_KEY=your_newsapi_key_here
```

`.env` is ignored by git. `.env.example` is provided as the template.

Get a free NewsAPI key at [newsapi.org](https://newsapi.org). The free tier allows 100 requests/day which is sufficient for normal use. If `NEWSAPI_KEY` is not set the app runs normally — the report just lacks live news context.

## News context

FRED data is backward-looking and cannot capture active geopolitical events, policy announcements, or market signals in real time. The news integration bridges this gap by fetching recent macro-relevant headlines at run time and injecting them into the LLM report prompt.

### What it does
- Fetches up to 8 headlines matching macro keywords (Federal Reserve, inflation, crude oil, geopolitical, recession, VIX, gold, yield curve, tariffs)
- Displays headlines in a collapsible panel above the dashboard
- Injects headlines into the LLM prompt so the narrative report can reference current events
- Accepts additional user-specified keywords and re-fetches on demand via the Refresh News button

### What it does not do
News headlines inform the narrative report only. They do **not** affect scores, weights, probabilities, triggers, or regime classification. The quantitative model stays clean and auditable. All model outputs are derived exclusively from FRED data and the user's manual shock input.

## Installation

**Recommended: conda**

```bash
conda create -n macro-analyzer python=3.11 -y
conda activate macro-analyzer
pip install -r requirements.txt
```

**Alternative: standard venv**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

## Run tests

```bash
pytest
```

## Notes on OpenAI API usage

The narrative report uses the OpenAI Chat Completions API (`client.chat.completions.create`). If `OPENAI_API_KEY` is missing, the app still runs the full analysis pipeline but report generation is disabled and replaced with a clear message.

## Getting started

1. Create the conda environment and install dependencies
2. Add your API keys to `.env` (FRED and OpenAI are required; NewsAPI is optional)
3. Run `streamlit run app.py`
4. Run a live analysis to verify scoring and scenario outputs against current FRED data
5. Run the three backtest cases to validate directional model behavior against known historical periods
6. Run `python -m scripts.calibrate_thresholds` to regenerate empirical thresholds from current FRED data

## Calibration methodology

### Data period
All constraint thresholds and scenario probability priors are calibrated against FRED data from **January 1996 to present**.

1996 was chosen as the start date because:
- It is the earliest date for which all required calibration series are available (`BAMLH0A0HYM2` begins January 1996)
- It falls within the post-Volcker, inflation-targeting monetary policy regime
- It captures the full dot-com cycle buildup (1996–2000), which is necessary for pre-recession signal calibration

Note: the free FRED API tier restricts `BAMLH0A0HYM2` to approximately the most recent 3 years for range queries. The calibration script uses a full-series fetch which may be subject to the same restriction. Re-run calibration with a paid FRED key or substitute the Baa–10y proxy series for full historical coverage.

### Recessions included
Calibration uses NBER recession dates (`USREC` series) with the following treatment:

| Recession | Dates | Included |
|---|---|---|
| Dot-com / 9-11 | Mar 2001 – Nov 2001 | ✓ Yes |
| Global Financial Crisis | Dec 2007 – Jun 2009 | ✓ Yes |
| COVID-19 | Feb 2020 – Apr 2020 | ✗ Excluded |
| 2022–23 near-miss | — | ✓ Yes (as stress period) |

### Why COVID is excluded
The COVID recession is excluded from all calibration because:
- It was an exogenous supply shock with no macro imbalance buildup — pre-recession signals look nothing like a normal cycle
- The policy response ($5T+ fiscal stimulus, rates to zero in two weeks, unlimited QE) was historically unprecedented and non-repeatable
- The resulting 2021–2023 inflation was a direct artifact of that policy collision with supply chain collapse, not organic demand-pull inflation
- Including it would calibrate thresholds only relevant if COVID-scale stimulus is repeated

The COVID exclusion window is **February 2020 – December 2021**.

### Threshold derivation
Thresholds use a hybrid empirical + policy-anchored approach:

- **Pre-recession window**: 12 months prior to each NBER recession start date
- **Moderate threshold**: 25th percentile of pre-recession values (earliest point where pre-recession distribution diverges from normal)
- **High threshold**: 75th percentile of pre-recession values (clearly elevated stress territory)

**Core PCE is the exception.** Empirical values (1.87% / 2.19%) were rejected because inflation was not the causal driver of either the 2001 or 2008 recessions — those levels reflect incidental low inflation, not a binding policy constraint. Core PCE thresholds are policy-anchored to the Fed dual-mandate tolerance bands and the post-2000 historical 2-3% inflation norm:
- Moderate (2.5%): persistently above the 2% target, Fed becomes cautious
- High (3.0%): policy flexibility materially constrained

All other series (unemployment, HY spread, yield curve) use empirically derived values.

Run `python -m scripts.calibrate_thresholds` to regenerate empirical values from FRED data. Use `--write` to update `config/calibration.py`.

### Probability priors
Scenario probabilities start from regime-conditional priors (see *Regime-conditional scenario priors* in the Model architecture section), not a fixed baseline. In Stress regime — the default for most of the cycle — priors are 45/30/25 (Base/Upside/Downside). In Stabilization regime they shift to 50/35/15; in Break regime to 30/20/50. The historical recession rate since 1996 (ex-COVID) is approximately 7.6% — lower than the 25% Stress-regime downside prior because NBER recessions are short relative to the full cycle and the downside scenario captures stress periods beyond outright recession.

## Market signals

VIX, WTI crude oil, and gold are included as real-time market signals alongside the FRED macro fundamentals. Unlike FRED macro series which are monthly and backward-looking, these update daily and reflect current market sentiment.

### Data sources

| Signal | FRED series | Frequency | Notes |
|---|---|---|---|
| VIX | `VIXCLS` | Daily | Market fear gauge |
| WTI Oil | `DCOILWTICO` | Daily | Crude oil price $/bbl |
| Gold | Yahoo Finance (GLD ETF) | Daily | GLD close × 10 ≈ gold spot $/oz. All FRED gold series are discontinued. Used for both live and backtest runs. |
| Initial jobless claims | `ICSA` | Weekly | YoY % change used as leading labor market signal in composite momentum |
| Household debt service ratio | `TDSP` | Quarterly | Used as dynamic leverage score in fragility. Defaults to 0 when unavailable. |

### How they feed into the model

| Signal | Feeds into | Mechanism |
|---|---|---|
| VIX | Fragility — liquidity score | VIX > 20: liquidity fragility = 1. VIX > 30: liquidity fragility = 2 (crisis) |
| WTI Oil | Fragility — energy dependency + energy/geo weight | High oil = input cost pressure + automatic energy_geo weight increase |
| Gold (YoY%) | Fragility — institutional score | Rising gold = institutional risk-off = loss of confidence signal |

### Impact on probabilities

Market signals affect probabilities **indirectly** through the fragility score:
- Higher fragility → heavier weight on financial and policy modules
- Fragility >= 7 triggers a direct downside probability adjustment (+10%)
- Max fragility is 9 (leverage 2 + liquidity 2 + energy 2 + correlation 1 + institutional 2)

### Oil and the energy/geo weight

Oil price drives the `energy_geo` module weight automatically:
- Oil > $75/bbl: energy_geo weight +5% (moderate pressure)
- Oil > $95/bbl: energy_geo weight +10% (severe pressure)

### Threshold decisions

| Signal | Threshold basis |
|---|---|
| VIX | Market convention (globally accepted: 20 = elevated, 30 = crisis) |
| Oil | Judgment-anchored to post-2005 shale-era supply dynamics ($75, $95) |
| Gold YoY | Judgment-anchored (15% = elevated safe-haven demand, 30% = crisis-level) |

## Backtesting

The backtesting module reruns the full model pipeline (constraint scoring, fragility, regime classification, scenario probabilities) against historical FRED data for a set of pre-defined periods. For each month in the period it computes the Downside Break probability midpoint and plots how it evolved over time.

The chart displays two lines: the faint thin line is the raw monthly score; the bold line is a 3-month rolling average. **Read the bold line.** The monthly line shows the threshold oscillation that is a structural property of hard-threshold scoring. The 3-month average filters that noise and reveals the underlying trend — which is the meaningful signal.

### Included backtest cases

| Case | Period | Rationale |
|---|---|---|
| Global Financial Crisis | 2007–2009 | Full credit cycle with pre-recession buildup — the primary validation case for threshold calibration |
| Inflation / Tightening | 2021–2023 | Tests model behavior during a post-COVID inflation regime with aggressive Fed tightening |
| Soft Landing / Insurance Cuts | 2018–2019 | Tests model behavior in a low-stress expansion with pre-emptive Fed cuts |

### FRED API data availability by backtest period

The free FRED API tier restricts the ICE BofA HY spread series (`BAMLH0A0HYM2`) to approximately the most recent 3 years. Requests for historical date ranges return empty data. This affects signal availability across backtest periods as follows:

| Signal | GFC 2007–2009 | Soft Landing 2018–2019 | Inflation 2021–2023 |
|---|---|---|---|
| Core PCE | Available | Available | Available |
| Unemployment | Available | Available | Available |
| Yield curve (10y–2y) | Available | Available | Available |
| VIX | Available | Available | Available |
| WTI Oil | Available | Available | Available |
| **HY Spread** | **Proxy (Baa–10y × 3.5)** | **Proxy (Baa–10y × 3.5)** | **Available (actual)** |
| Gold (GLD ETF) | Available | Available | Available |

**How the proxy works:**

For periods where `BAMLH0A0HYM2` returns no data, the backtesting module automatically substitutes the Moody's Baa corporate yield (`BAA`) minus the 10-year Treasury yield (`DGS10`), scaled by 3.5× to approximate HY-spread equivalence. Both `BAA` and `DGS10` are freely available on FRED back to the 1950s with no tier restrictions.

The proxy tracks the same credit risk premium — excess yield over risk-free — at investment-grade quality (Baa/BBB) rather than high-yield (BB and below). The 3.5× scaling factor reflects the historical ratio between these two spreads across multiple credit cycles. With this substitution, the financial constraint score, credit interaction terms, and credit stress trigger all function normally for GFC and soft-landing backtests. Absolute probability levels will differ slightly from a run using the actual HY spread, but direction, timing of threshold crossings, and regime classification remain valid.

For inflation cycle (2021–2023), the actual `BAMLH0A0HYM2` series is used directly — no proxy needed.

### What each backtest case tests

**Global Financial Crisis (2007–2009)**

This is the primary stress-detection validation case. The model should show a rising downside trend through 2007 as credit conditions deteriorated (Baa spread proxy rising, yield curve flattening), a sustained peak through mid-to-late 2008 as unemployment climbed, the yield curve fully inverted, and VIX spiked, then a gradual decline into late 2009 as the policy response stabilized credit markets. The meaningful signal is the shape and duration of elevation through 2008 — the model should track the buildup, not just react at the peak. Credit spread data uses the Baa–10y proxy for this period (see *FRED API data availability* above).

**Inflation / Tightening (2021–2023)**

This case tests the model's inflation constraint logic. Through 2021, core PCE had not yet crossed the 2.5% moderate threshold and the policy constraint should score 0 — the model should sit flat in Stabilization or low Stress regime. From early 2022, as core PCE crossed 2.5% then 3.0% and the Fed began aggressive hikes, the policy constraint should step up sharply. The yield curve then inverted through 2022–2023, keeping the constraint score elevated even as inflation began falling. This illustrates a key model property: the constraint score responds to whether pressure has *resolved*, not just whether the direction has improved. The model should remain in Stress regime through most of 2023. This is the most complete backtest — actual HY spread data is available for this period.

**Soft Landing / Insurance Cuts (2018–2019)**

This case validates that the model does not generate false stress signals in a benign expansion. Core PCE was below 2.5% throughout, unemployment was low and stable, and the only active signal was the yield curve flattening toward and occasionally crossing the 0.52% warning threshold. The model should stay in Stress or Stabilization regime with a flat, low downside trend for the full period, with minor oscillation from the yield curve hovering near its threshold. A mild drift upward in late 2019 is expected from the three pre-emptive Fed cuts and repo market stress — but no sustained elevation. Net change close to zero is the correct result.

### How to interpret the chart

The backtesting view shows two lines: a faint monthly raw score and a bold 3-month rolling average. **Read the rolling average.** Hard-threshold scoring causes the monthly line to oscillate when a series hovers near a boundary — this is a structural property of the model, not noise in the data. The rolling average filters that oscillation and reveals the underlying trend.

What matters:
- **Direction and duration**: A sustained upward trend means genuine stress accumulation. A brief spike that reverts is a single noisy data point.
- **Shape, not absolute level**: The model's probability range is bounded by design (see Known limitations). Compare the shape of each period against the others, not the raw numbers.
- **Start/end metrics**: The summary Start/End/Change statistics at the top of the backtest view capture only the endpoints. For GFC — where stress built through the middle of the period — these numbers are less informative than the chart itself.

### What the model does and does not tell you

The model identifies when macro conditions have moved into territory that historically precedes stress. It does not predict whether that stress leads to a recession — that depends on factors (policy response, external shocks, sequencing) the model cannot capture. Use the backtest to calibrate your intuition for what "elevated" looks like in this framework, not to validate specific probability numbers.

### COVID excluded from backtesting

The COVID shock (2019–2021) is excluded from backtest cases for the same reason it is excluded from calibration: it was an exogenous supply shock with no macro imbalance buildup. The model's thresholds were derived without COVID data and are not designed to handle that regime.

### Current limitations of the backtest module

The current implementation tracks only the Downside Break probability over time. It does not:
- Score whether scenario calls were correct against realized outcomes
- Measure early warning lead time before recession onset
- Evaluate regime classification accuracy
- Compare model performance against a baseline

This is a known limitation. The module is currently a visualization tool, not a full validation framework.

## Known limitations

Understanding these limitations is essential before relying on any output from this tool.

### 1. Lagging indicators

The primary data source is FRED. Most FRED macro series (Core PCE, unemployment, HY spreads) are reported monthly with a 4–8 week publication lag. The model is structurally backward-looking. It can identify that stress has built up but it will not signal the beginning of a crisis in real time. During the 2007–2009 backtest the model correctly tracked the slow deterioration through 2007–early 2008, but the sharpest stress (September–October 2008) was not the model's best moment — the financial system was moving faster than monthly data.

### 2. Threshold instability near boundaries

All scoring uses hard thresholds: a series either crosses a boundary or it does not. When a series hovers near a threshold it can cross in and out monthly, producing oscillating scores. This is most visible in the 2018–2019 soft landing backtest: the yield curve spread repeatedly crossed the 0.52 moderate threshold, causing the model to alternate between Turbulence and Expansion regimes month to month. This is a structural property of hard-threshold scoring, not a data error. The backtest chart mitigates this visually with a 3-month rolling average, but the underlying scores remain binary.

### 3. Bounded probability range

The Downside Break scenario ranges from roughly 0.15 (clean Stabilization regime) to 0.50+ (Break regime with high constraint and fragility). Scenario floors prevent near-0% or near-100% readings by design. In the most common environment (Stress regime, moderate scores), the range is typically 0.25–0.42. This is intentional for communication discipline — the model is not a calibrated statistical forecast. Treat the direction and relative level (rising vs. falling, elevated vs. low) as the signal, not the absolute number.

### 4. Small calibration sample

Thresholds are derived from two recession cycles: 2001 and 2008. This is an inherently small sample. The model cannot claim statistical robustness — it claims structural logic anchored to the most relevant historical analogs available. Any threshold recalibration should proceed cautiously and document the reasoning for each change.

### 5. Geopolitical shocks are manually overridden

The model has no automated geopolitical signal. Active conflicts, sanctions, and supply disruptions (e.g., Strait of Hormuz closure, energy embargo) must be entered manually via the shock severity override in the sidebar. If this is not updated the model will remain in a macro-data-only regime and miss the geopolitical dimension entirely. Use the news refresh and shock classifier suggestion as a prompt, but verify independently.

### 6. FRED API restrictions on historical credit spread data

The ICE BofA HY spread series (`BAMLH0A0HYM2`) is restricted to approximately the most recent 3 years under the free FRED API tier. For backtests outside that window (GFC 2007–2009 and soft landing 2018–2019), the model automatically substitutes a proxy: Moody's Baa corporate yield (`BAA`) minus the 10-year Treasury (`DGS10`), scaled by 3.5× to approximate HY-spread equivalence. Both proxy series are freely available on FRED back to the 1950s. The substitution allows the financial constraint score, credit interaction terms, and credit stress trigger to function normally for all backtest periods. The inflation cycle (2021–2023) uses the actual HY spread and is unaffected. See the *FRED API data availability* section under Backtesting for the full signal matrix.

### 7. Model does not know what it does not know

The rule set is compact. Novel macro regimes — a sovereign debt crisis in a G7 country, simultaneous supply and demand shocks, debt deflation — may not be captured. When the macro environment looks structurally different from 2001 or 2008, treat model outputs with additional skepticism.
