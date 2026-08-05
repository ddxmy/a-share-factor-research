# Research Protocol

## Question and boundary

The protocol evaluates weekly cross-sectional return ranking in the historical
CSI 300. It does not test custom factors, XGBoost, neural networks, multiple
label horizons, a full-A-share primary universe, or portfolio optimization.
The objective is disciplined comparison of a linear benchmark and constrained
tree-model variants, not maximization of a backtest statistic.

## Point-in-time panel

For every weekly signal date, membership must be the CSI 300 set effective on
that date. Regular index changes are mapped to their effective dates and any
temporary changes require separate event evidence. The panel excludes a name
until 61 valid daily observations are available. This preserves the 60-day
maximum Alpha158 operator lookback without silently shortening history.

The signal is available after the last trading-day close of the week. Entry is
the next trading-day open; exit is the open following the next weekly signal.
Both stock entry/exit prices use the same-day `open × adj_factor`; the benchmark
uses the corresponding CSI 300 open return. The label is stock return minus
benchmark return. Missing prices make a label ineligible rather than being
forward-filled.

## Features and preprocessing

The 158 Qlib Alpha158 features are fixed to the Qlib source pin in
`../config/research_v1.json`. The local implementation's limited 10-security,
20-date numerical parity check passed with finite-value absolute error at most
`1e-6`. Feature values are taken from the latest valid base-data date on or
before the signal date, with a default five-trading-day freshness rule.

Preprocessing is done independently within each signal-date cross section:

- Convert positive and negative infinity to missing values.
- Impute the cross-sectional median.
- Winsorize at median plus or minus `5 × 1.4826 × MAD`.
- Standardize with population standard deviation (`ddof=0`).

All-null and zero-variance features become zero and must be recorded as quality
events. No custom or fundamental features are mixed into this v1 experiment.

## Purged evaluation

The five folds are: 2015–2019/2020/2021,
2016–2020/2021/2022, 2017–2021/2022/2023,
2018–2022/2023/2024, and 2019–2023/2024/2025
(train/validation/test). The purge condition is based on realized label end:
every prior-stage `label_end_date` must be strictly before the next stage's
first signal date. Test periods are not used for model selection.

Ridge is a pooled, weekly-equal-weight linear baseline. G5 is the frozen local
LightGBM search. G5-Z expands that local search with validation-only selection.
R1 carries Qlib-style LightGBM parameters while applying the documented
cross-sectional label scale treatment. All models receive identical
point-in-time inputs and use industry/size-residualized scores for the
neutralized comparison.

Each week produces a Spearman Rank IC. Summaries report equal-week mean Rank
IC, standard deviation, ICIR, positive-week ratio, annual summaries, and
cumulative IC. Means and prespecified paired differences use Bartlett
Newey–West HAC standard errors with lag four. The locked neutralized results
are G5 0.0137, G5-Z 0.0164, and R1 0.0210. G5-Z's paired HAC comparisons with
G5 (`p=0.438`) and R1 (`p=0.158`) are not significant at 5% two-sided; the
observed averages therefore support only descriptive comparison.

## Trading diagnostic and limitations

The Top-50 diagnostic ranks neutralized scores, holds 50 names equally, and
rebalances weekly at the next open. It enforces suspension and price-limit
blocks, keeps failed sells, updates cash and holdings only from actual fills,
and charges 0/10/20 bps per side only on actual notional. It is a diagnostic,
not proof of implementability.

This repository contains no market data, model panels, predictions, logs, or
notebooks. Reproduction requires an independently licensed private data source
and may differ because of data revisions, corporate-action treatment, index
membership reconstruction, market microstructure, or execution assumptions.
The parity check is limited; neutralization is not a full risk model; historical
Rank IC and backtests do not establish future performance, capacity, or
investment suitability.
