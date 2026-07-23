# Local Factor Evaluation Protocol

## Contents

1. Evaluation identity
2. Preprocessing and labels
3. Hard gates
4. Quality score
5. Statistical correction
6. Correlation and replacement
7. Library tiers and controls
8. Calibration and versioning

## 1. Evaluation identity

Treat each result as a function of five immutable identifiers:

```text
formula_hash
data_snapshot
universe_version
label_version
evaluator_version
```

Never compare or replace factors across incompatible evaluator versions without re-evaluating
both under the same protocol.

## 2. Preprocessing and labels

Compute factor inputs with data available through the close of date `t`. Use unadjusted raw
OHLC fields plus the point-in-time adjustment-factor series to construct continuous price
features. Do not normalize realized returns by board price-limit width.

Apply these cross-sectional transformations independently on each date:

1. mask the point-in-time universe and tradable observations;
2. winsorize at the configured tail bounds;
3. regress on industry dummies and log float market capitalization;
4. retain the residual;
5. z-score the residual.

Store raw and neutralized diagnostics. Use the neutralized signal as the primary score input.

Primary label:

```text
close[t+1] / open[t+1] - 1
```

Secondary label:

```text
adjusted_close[t+1] / adjusted_close[t] - 1
```

Freeze the direction from mean discovery-sample Rank IC. Do not reorient on validation,
transfer universes, secondary labels, or lockboxes.

## 3. Hard gates

Apply gates before scoring.

### Formula and panel gate

- no future reference or label-derived field;
- panel-valued output indexed by date and security;
- average coverage at least 95%;
- usable cross-section on at least 95% of evaluation dates;
- median daily unique values at least 30;
- finite-value and zero-denominator checks pass;
- no canonical or rank-equivalent duplicate.

### Core statistical gate

After discovery direction is frozen:

```text
discovery neutralized Rank IC >= 0.01
validation neutralized Rank IC >= 0.01
positive validation half-years >= 3/4
validation one-sided Newey-West t >= 2.5
global candidate-history BH-FDR q <= 0.10
```

Mark `t >= 3.0` as strong statistical evidence. Keep candidates with IC in `[0.005, 0.01)`
in the research tier only when they are genuinely independent.

### Robustness gate

Require a positive neutralized validation IC and retain at least 40% of the raw absolute IC.
Require non-negative validation IC on the primary transfer check. Permit a documented exception
only when the economic mechanism is explicitly universe-specific.

### Economic gate

Use `PASS`, `CONDITIONAL`, or `FAIL`:

- `PASS`: coherent mechanism, valid dimensions, nontrivial transformation;
- `CONDITIONAL`: plausible but likely a known style proxy;
- `FAIL`: tautological, forward-looking, degenerate, or economically incoherent.

Never admit `FAIL` to the core library.

## 4. Quality score

Read weights and linear bounds from `quality_score_v1.json`. For a higher-is-better metric:

```python
scale = clip((x - low) / (high - low), 0, 1)
points = weight * scale
```

For a lower-is-better metric:

```python
points = weight * (1 - scale)
```

The 100 points are:

| Section | Points | Metrics |
|---|---:|---|
| Predictive power | 35 | discovery IC, validation IC, validation ICIR, IC retention |
| Time stability | 25 | monthly hit rate, half-year signs, worst half-year IC, parameter stability |
| Portfolio quality | 15 | quantile monotonicity, 10 bps Sharpe, 20 bps retention, drawdown |
| Robustness | 15 | neutralization retention, CSI 500, liquid all-A, secondary label |
| Independence/implementation | 10 | max correlation, turnover, coverage |

Define ICIR as `mean(daily IC) / std(daily IC)` without annualization. Report
`annualized_icir = sqrt(252) * icir` separately.

If inputs are missing, report:

```text
observed_points
available_weight
score_completeness = available_weight / 100
normalized_observed_score = 100 * observed_points / available_weight
```

Never call the normalized observed score a formal quality score. The formal score exists only
when every required metric and hard gate is available.

## 5. Statistical correction

Compute the validation mean-IC t statistic with a Newey-West long-run variance estimate. Use a
one-sided p-value only because direction was fixed independently on discovery data.

Apply Benjamini-Hochberg FDR to every unique evaluated candidate under the evaluator version,
not merely the latest batch. Keep invalid formulas in the trajectory but exclude candidates
without a valid statistical test from the BH denominator.

Synthetic controls used for calibration do not enter the production candidate-history FDR.

## 6. Correlation and replacement

Compute daily cross-sectional Spearman correlation between two factor panels, then average the
absolute daily correlations over time. Do not use a single flattened full-panel correlation.

Default thresholds:

```text
hard duplicate:          |rho| >= 0.95
replacement/dedup gate:  |rho| >= 0.50
high redundancy label:   |rho| >= 0.80
```

For a candidate whose maximum library correlation is below 0.50, allow admission if all other
gates pass. For correlation at or above 0.50, replace only when:

1. it beats the best match by at least 5 quality points;
2. validation IC improves by at least 10%;
3. it does not correlate at 0.50 or above with another library factor;
4. stability and turnover do not materially deteriorate.

Greedily deduplicate each batch in descending quality-score order.

## 7. Library tiers and controls

Use these score bands only after hard gates:

```text
research:   score >= 55, retained for observation
qualified:  score >= 65, eligible for core admission
strong:     score >= 75
core:       score >= 85 and strong statistical evidence
```

Maintain separate versioned artifacts:

- an append-only candidate trajectory containing everything;
- a broad research library;
- a deduplicated predictive core used for synthesis;
- a stricter tradable core used for standalone portfolio claims;
- a benchmark/control library used only for calibration and comparison.

The predictive core requires all formula, statistical, robustness, economic, FDR, score, and
deduplication gates. Transaction-cost and turnover metrics contribute to its score but are not a
universal hard gate: high-turnover predictive signals may still add value after model combination
or portfolio-level turnover control.

The tradable core is a subset of predictive core and additionally requires:

```text
10 bps net annualized Sharpe > 0
20 bps net annualized Sharpe >= 0
documented execution price and rebalance convention
```

Keep legacy FactorMiner factors, representative Alpha158 factors, classic factors, synthetic
noise, and deliberately invalid controls in the benchmark/control library. Never count them as
local admissions or deduplicate them away merely to improve the local-library comparison.

Read `campaign_protocol.md` for campaign budgets, validation isolation, freeze requirements, and
the mandatory comparison matrix.

## 8. Calibration and versioning

Before freezing v1, evaluate fixed positive and negative controls:

- existing FactorMiner formulas;
- representative Alpha158 factors;
- classic momentum, reversal, volatility, liquidity, and volume-price factors;
- random-noise panels;
- constant, scalar, and deliberately forward-looking invalid controls.

Check score distributions, false-pass rates, component saturation, and whether known invalid
controls are rejected at the correct gate. Record all changes before freezing thresholds.

The current short close-to-close, non-neutralized calibration is provisional. Freeze formal v1
only after the full 2015-to-present data contract is met.
