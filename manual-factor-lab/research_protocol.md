# Manual Factor Laboratory Research Protocol

## Purpose and boundary

This laboratory is a pre-registered evaluation plan for the ten factor IDs in
`factor_registry.csv`. It contains no market data, calculated signals, results,
or factor formulas in executable form. Each factor remains researcher-owned:
the researcher must implement it against a licensed, point-in-time daily panel
and retain an auditable implementation record before evaluating it.

## Data and timing contract

The eligible universe is point-in-time CSI 300 membership on each weekly signal
date. Required fields and exact definitions are frozen in the registry. Daily
prices must use a consistent corporate-action convention; volume, turnover,
traded amount, and market return must be time-aligned to the same session.
Signals use only observations through the signal-date close and are eligible
for execution at the next trading-day open. Securities without the full stated
lookback, required fields, or valid next-open label are excluded for that date;
no lookback is shortened and no missing observation is forward-filled.

The outcome is each security's next weekly adjusted open-to-open return less
the contemporaneous CSI 300 adjusted open-to-open return. Signal values are
cross-sectionally median-imputed, MAD-winsorized, and standardized only after
the raw factor is calculated; the raw factor definition itself is never changed
to improve performance.

## Pre-registered single-factor tests

For every factor separately, evaluate weekly cross-sectional Spearman Rank IC
against the outcome over the five locked out-of-sample test years 2021--2025.
Report the equal-week mean Rank IC, standard deviation, ICIR, positive-week
ratio, annual summaries, and cumulative Rank IC. Estimate the mean Rank IC
with a Bartlett Newey--West HAC standard error using lag four. The sign test is
one-sided in the pre-registered direction from the registry; all other
diagnostics are descriptive.

Use the five frozen rolling folds: 2015--2019/2020/2021,
2016--2020/2021/2022, 2017--2021/2022/2023, 2018--2022/2023/2024, and
2019--2023/2024/2025 (train/validation/test). A split is purged so every prior
label end date is strictly before the following segment's first signal date.
The test periods may not be used for formula selection, direction changes,
threshold tuning, or implementation repair.

## Admission criteria

A factor is admitted from `planned` only when all conditions hold:

1. Its researcher implementation is reviewed against the registry's frozen
   definition, required fields, and next-open availability rule.
2. It has at least 156 eligible weekly out-of-sample observations across the
   locked 2021--2025 test period.
3. Its mean weekly Rank IC has the pre-registered direction and a one-sided
   HAC p-value below 0.05.
4. Its mean Rank IC has the same direction in at least four of the five
   calendar test years.

Admission is evidence for this fixed historical protocol, not evidence of a
deployable investment strategy. Failed factors remain recorded as planned or
rejected with their implementation and diagnostic record; they are not
redefined or silently dropped.
