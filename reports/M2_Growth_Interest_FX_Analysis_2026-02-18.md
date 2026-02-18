# Broad Money Dynamics Across Major Economies: Interactions with Interest Rates and Exchange Rates (1980–2024)

**Date:** 2026-02-18  
**Prepared for:** Simon  
**Prepared by:** PiClaw Research Assistant  

---

## Abstract

This report studies how broad money (M2 proxy), lending interest rates, and exchange-rate movements interact across a multi-country panel of large economies. The empirical sample is constructed from publicly available annual macro-financial data (1980–2024 where available), combining World Bank broad money and lending-rate indicators with foreign-exchange conversion data sourced from Yahoo Finance (via `yfinance`) and a World Bank official FX fallback.

Three findings stand out. First, broad money growth exhibits substantial persistence, especially in countries with historically rapid financial deepening. Second, there is heterogeneity in the interest-rate–money-growth relationship across countries, but pooled estimates show a modest positive conditional association in this annual-frequency panel. Third, contemporaneous FX changes against the U.S. dollar contribute less explanatory power than interest-rate and lagged money-growth terms, once country effects are included.

From a policy perspective, these results are consistent with institutional evidence from major central banks: broad monetary aggregates respond not only to policy rates but also to banking system structure, liquidity regulation, and non-linear policy regimes (including quantitative easing/tightening phases). Therefore, M2 should be interpreted as a state variable in macro-financial transmission, rather than as a standalone policy target.

---

## 1. Research question and motivation

The policy relevance of broad money has evolved substantially since the 1980s. In high-inflation episodes and under financial liberalization, money growth has often been viewed as an early warning signal for nominal demand pressure. In contrast, under post-2008 unconventional policy regimes, large central bank balance-sheet adjustments and shifts in deposit behavior have complicated direct monetary targeting.

This report addresses a practical question for cross-country macro analysis:

> **How are M2 growth, lending interest rates, and exchange-rate shifts jointly related across major economies over long horizons?**

The answer matters for comparative macro monitoring, especially when users want a common-currency view of money stock levels while preserving country-level dynamics.

---

## 2. Data sources and construction

### 2.1 Core indicators

The analysis uses the following public indicators:

1. **Broad money (current local currency units)**: World Bank `FM.LBL.BMNY.CN`  
2. **Broad money growth (annual %)**: World Bank `FM.LBL.BMNY.ZG`  
3. **Lending interest rate (%)**: World Bank `FR.INR.LEND`  
4. **Official exchange rate (LCU per USD, period average)**: World Bank `PA.NUS.FCRF` (fallback only)  
5. **FX market series**: Yahoo Finance via `yfinance` (primary annual-average FX conversion input)

### 2.2 Country coverage and period

A balanced conceptual universe (largest economies) was attempted; practical coverage is constrained by indicator availability and continuity. The analysis sample contains 7 economies with sufficient data continuity:

- United States (US)
- China (CN)
- Japan (JP)
- India (IN)
- United Kingdom (GB)
- Brazil (BR)
- Canada (CA)

Observed panel span (effective): **1980–2024**, with varying missingness by variable/country.

### 2.3 FX conversion and common-basis normalization

For visual comparison of M2 levels, each country’s local-currency broad money is converted to a selected base currency using annual average FX rates. The conversion for country *i* in year *t* is:

\[
M2^{(base)}_{i,t} = \frac{M2^{(LCU)}_{i,t} \times (USD/LCU)_{i,t}}{(USD/base)_{t}}
\]

The app reports these values as **billions of base currency**, ensuring one common basis across all selected countries.

---

## 3. Methodology

### 3.1 Descriptive diagnostics

The first layer of analysis computes country-specific correlations:

- corr( M2 growth, lending rate )
- corr( M2 growth, FX appreciation vs USD )

where FX appreciation is the annual percentage change in USD per local currency (positive = local appreciation vs USD).

### 3.2 Panel regression

A pooled annual-frequency regression with country fixed effects is estimated:

\[
\Delta M2_{i,t} = \alpha + \beta_1 \cdot Rate_{i,t} + \beta_2 \cdot FX_{i,t} + \beta_3 \cdot \Delta M2_{i,t-1} + \gamma_i + \varepsilon_{i,t}
\]

- Dependent variable: annual broad money growth (%)
- Regressors: lending rate, FX change, lagged M2 growth
- Controls: country fixed effects (dummy structure)

This is an exploratory reduced-form model (not a causal identification design).

### 3.3 Event windows

To contextualize structural breaks, ±1-year windows are computed around major macro-political episodes (e.g., 2008 GFC, 2020 COVID policy shock, 2022 energy/inflation shock period).

---

## 4. Empirical findings

### 4.1 Panel scope and fit

- Observations in core panel: **296 annual rows**
- Countries: **7**
- Regression sample (complete cases): **241**
- Estimated model fit: **R² ≈ 0.215**

Interpretation: at annual frequency, and with limited covariates, roughly one-fifth of variation in M2 growth is captured. This is plausible given the omitted roles of regulation, banking structure, crises, and policy regime changes.

### 4.2 Coefficient estimates (pooled OLS with FE)

Key slope estimates:

- **Lending rate coefficient:** +0.233 (t ≈ 1.80)
- **FX change coefficient:** +0.043 (t ≈ 0.29)
- **Lagged M2 growth coefficient:** +0.145 (t ≈ 2.22)

Two practical inferences:

1. **Persistence matters**: lagged M2 growth is the strongest predictor among included regressors (in t-stat terms).
2. **Interest-rate link is regime-sensitive**: the positive sign does **not** imply that higher policy rates mechanically expand money. Rather, in this panel it likely reflects mixed regimes where lending rates can co-move with inflation and nominal expansion in certain countries/periods.

### 4.3 Country-level correlation heterogeneity

Representative results:

- China: corr(M2 growth, lending rate) ≈ **0.73**
- India: corr(M2 growth, lending rate) ≈ **0.50**
- UK: corr(M2 growth, lending rate) ≈ **0.31**
- US: corr(M2 growth, lending rate) ≈ **0.32**
- Canada: corr(M2 growth, lending rate) ≈ **0.03**

These differences reinforce that monetary transmission is institutional: market depth, bank competition, reserve frameworks, capital controls, and liability composition all matter.

### 4.4 Recent-period profile (2015–2025 sample slice)

Average M2 growth ranking in this sample slice:

1. Brazil: **11.28%**
2. India: **10.38%**
3. China: **9.61%**
4. United States: **6.46%**
5. United Kingdom: **5.09%**
6. Japan: **2.96%**

Stylized interpretation:

- Faster nominal deepening economies tend to retain higher broad-money growth.
- Mature low-rate systems (e.g., Japan) show structurally lower money growth, even with prolonged accommodation.

### 4.5 Event-window behavior

Selected episodes:

- **2008 GFC**: event-year mean M2 growth ≈ **13.99%**
- **2020 COVID policy shock**: event-year mean M2 growth ≈ **12.30%**
- **2022 energy/inflation shock window**: event-year mean M2 growth ≈ **6.89%**, while average lending rates in the ±1 window rose substantially (≈ **17.25%** in pooled sample, influenced by high-rate jurisdictions)

This sequence is consistent with post-crisis liquidity expansion followed by normalization/tightening.

---

## 5. Economic interpretation

### 5.1 Growth-rate channel

Broad money growth tracks credit creation, deposit accumulation, and portfolio shifts between liquid and less-liquid instruments. The ECB’s monetary-aggregate framework explicitly links aggregate movements to counterpart balance-sheet items, including private-sector credit and government claims. This supports using M2 as a system-level liquidity measure, not a single-policy-instrument metric.

### 5.2 Interest-rate channel

Interest rates influence money creation through several mechanisms:

- Loan demand and debt service burden
- Deposit substitution and term structure effects
- Bank funding costs and margin behavior
- Expectations and inflation compensation

Because these channels can offset each other across regimes, the reduced-form relationship is expected to vary by country and period. The BoE’s policy documentation on QE/QT and the BIS evidence on negative-rate transmission both highlight non-linear responses when conventional policy space is constrained.

### 5.3 FX channel

Exchange-rate effects appear weaker in contemporaneous annual regressions in this sample. A plausible interpretation is that FX influences M2 indirectly and with lags via trade balances, capital flows, reserve operations, and domestic policy response. The BIS discussion of negative-rate environments and exchange-rate pressures underscores that FX often enters through policy reaction functions rather than one-step mechanical pass-through.

---

## 6. Policy implications

1. **Avoid single-indicator policy conclusions.** M2 should be combined with inflation expectations, credit composition, and term-structure indicators.
2. **Use common-currency normalization for comparison, but retain local diagnostics.** A unified base currency improves visual comparability, while local-currency and institutional context remain essential for interpretation.
3. **Model regime shifts explicitly.** Crisis and post-crisis policy phases alter transmission parameters.
4. **Event-aware monitoring adds value.** Annotated macro-political events improve interpretation of inflection points in money series.

---

## 7. Limitations

- Country definitions of broad money differ in detail, reducing strict comparability.
- Annual frequency smooths high-frequency policy transmission.
- The regression is exploratory and not designed for causal inference.
- Some country-variable pairs have missingness (notably lending-rate coverage in specific windows).
- FX source hierarchy (yfinance primary, World Bank fallback) introduces mixed-source measurement risk, though this is documented and transparent.

---

## 8. Conclusion

Across major economies, broad money dynamics over 1980–2024 show persistence, regime dependence, and structural heterogeneity. Interest rates and exchange rates are relevant but insufficient as standalone predictors of M2 growth in long-run pooled annual data. For cross-country monitoring, the strongest practical approach is a dual framework:

- **Comparable levels view**: common-base-currency M2 visualization
- **Country-structural view**: local monetary institutions, policy regime, and event context

The updated M2 tracker implements this design directly: long history, base-currency selection, common-basis normalization, and event-aware hover tags.

---

## References (public sources)

1. World Bank Open Data. **Broad money (current LCU), FM.LBL.BMNY.CN**.  
   https://data.worldbank.org/indicator/FM.LBL.BMNY.CN

2. World Bank Open Data. **Broad money growth (annual %), FM.LBL.BMNY.ZG**.  
   https://data.worldbank.org/indicator/FM.LBL.BMNY.ZG

3. World Bank Open Data. **Lending interest rate (%), FR.INR.LEND**.  
   https://data.worldbank.org/indicator/FR.INR.LEND

4. World Bank Open Data. **Official exchange rate (LCU per US$, period average), PA.NUS.FCRF**.  
   https://data.worldbank.org/indicator/PA.NUS.FCRF

5. European Central Bank. **Monetary aggregates: definitions and counterparts**.  
   https://www.ecb.europa.eu/stats/money_credit_banking/monetary_aggregates/html/index.en.html

6. Federal Reserve Bank of St. Louis (FRED). **M2 [M2SL] metadata and series notes**.  
   https://fred.stlouisfed.org/series/M2SL

7. Bank of England. **Quantitative easing (QE) explainer**.  
   https://www.bankofengland.co.uk/monetary-policy/quantitative-easing

8. Bank for International Settlements. **How have central banks implemented negative policy rates?** BIS Quarterly Review (March 2016).  
   https://www.bis.org/publ/qtrpdf/r_qt1603e.htm

9. Yahoo Finance (accessed via `yfinance`). **FX market time series**.  
   https://finance.yahoo.com/

---

## Appendix A — Key model outputs

- Sample coverage: 296 observations, 7 countries, 1980–2024 effective window
- Pooled OLS (with country FE):
  - `lending_rate_pct`: +0.233 (t ≈ 1.80)
  - `fx_change_pct`: +0.043 (t ≈ 0.29)
  - `m2_growth_lag1`: +0.145 (t ≈ 2.22)
  - Model R²: 0.215

## Appendix B — Reproducibility files

- Dataset build script: `scripts/build_m2_dataset.py`
- Analysis script: `scripts/analyze_m2_macro_links.py`
- Built dataset: `docs/data/m2_long_history.json`
- Analysis output: `reports/m2_macro_analysis_summary.json`
