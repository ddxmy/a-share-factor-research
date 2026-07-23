# Pattern State Metrics

Use this reference when updating FactorMiner memory, pattern states, or forbidden regions.
The goal is to keep all agents using the same definitions for `saturation_score` and
`low_yield_score`.

## Purpose

Pattern diagnostics must distinguish two different failure modes:

- `saturation_score`: a pattern was historically useful, but its local search region is now
  crowded. Recent candidates increasingly correlate with existing library factors, admitted
  yield declines, and best-score improvement plateaus.
- `low_yield_score`: a pattern has been tried enough times, but it has not shown enough
  scoring power. It has low pass rate and low average score.

Do not treat low recent success rate alone as saturation. Saturation means "previously
productive but now overpopulated"; low yield means "not proven useful after enough attempts".

Both diagnostics can lead to `forbidden_regions`, but with different reasons:

```json
{"direction": "VWAP Deviation Variants", "reason": "saturated_high_corr"}
{"direction": "Noisy Microstructure Moment", "reason": "persistent_low_score"}
```

## Required Helpers

Use these canonical helper functions:

```python
from math import exp


def clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def sigmoid(x):
    return 1.0 / (1.0 + exp(-x))
```

`clip(x, 0, 1)` truncates a value into the `[0, 1]` interval.

## Shared Fields

These fields should be tracked per pattern.

```text
attempt_count:
  Total number of candidate formulas attempted for this pattern.

pass_count:
  Number of candidates with score >= pass_threshold.

high_quality_count:
  Alias of pass_count in the current implementation. Keep this name only for future
  compatibility with multi-stage evaluation, where "high quality" may later mean passing a
  fast IC screen before full validation.

admitted_count:
  Number of candidates finally admitted to the library. Count decisions in {admit, replace}
  after intra-batch dedup rollback is applied.

avg_score:
  Historical average score over all attempted candidates for this pattern.

best_score:
  Historical best score over all attempted candidates for this pattern.

recent_high_quality_count:
  Alias of recent_pass_count in the current implementation.

recent_attempt_count:
  Number of candidate records in the recent rolling window for this pattern.

recent_pass_count:
  Number of recent candidates with score >= pass_threshold.

recent_admitted_count:
  Number of recent candidates finally admitted to the library.

recent_p75_max_corr:
  75th percentile of recent high-quality candidates' max absolute correlation with the
  existing library. Use 0.0 when no correlation records exist.

historical_best_before_recent:
  Best score before the recent window starts.

recent_best_score:
  Best score within the recent window.
```

Canonical recent window:

```text
recent means a pattern-level rolling window, not the latest global iteration.

Use the most recent 20 candidate records for the pattern by default. If fewer than 20 exist,
use all available records. Do not define recent as "the latest iteration", because a single
iteration may contain only 0-2 candidates for a given pattern and will be too noisy.
```

## Default Parameters

Use these defaults unless the user explicitly asks for calibration:

```python
PASS_THRESHOLD = 30.0
CORR_THRESHOLD = 0.5

EVIDENCE_SCALE = 8.0
SUCCESS_SCALE = 1.5
COVERAGE_SCALE = 4.0

CORR_TEMP = 0.05
YIELD_MARGIN = 0.15
YIELD_TEMP = 0.10
SCORE_DELTA = 3.0

RECENT_WINDOW = 20
MIN_SATURATION_ATTEMPTS = 16
MIN_SATURATION_ADMITTED = 3
MIN_RECENT_ATTEMPTS = 5
MIN_RECENT_PASS = 2

MIN_LOW_YIELD_ATTEMPTS = 16

DEPRIORITIZE_THRESHOLD = 0.45
RESTRICT_THRESHOLD = 0.60
FORBIDDEN_THRESHOLD = 0.70
```

Parameter intuition:

```text
EVIDENCE_SCALE:
  About 8 attempts are needed before a pattern state should be trusted.

SUCCESS_SCALE:
  One or two admitted factors are enough to establish that this pattern has been productive.

COVERAGE_SCALE:
  Around 4 admitted factors indicate meaningful local coverage.

CORR_TEMP:
  Controls how sharply corr_pressure rises around CORR_THRESHOLD.

YIELD_MARGIN:
  Small admitted-yield fluctuations below 0.15 should not be overinterpreted.

SCORE_DELTA:
  A score improvement below about 3 points is not considered a major breakthrough.

RECENT_WINDOW:
  Recent is computed per pattern from the latest 20 candidate records, not from the latest
  global iteration.

FORBIDDEN_THRESHOLD:
  Start with 0.70, not 0.80. The nonlinear gates already make the scores conservative.
  Safety should come from minimum evidence requirements, not from an overly high score
  threshold.
```

These defaults are calibration starting points. After enough mining logs exist, tune them by
reviewing whether patterns marked as `restricted` or `forbidden` actually continued to produce
novel admitted factors in later runs.

Do not silently change metric parameters. If experiments suggest different thresholds or
scales, update `references/pattern_state_metrics.md` and record the rationale before using
the new values.

## Saturation Score

Use saturation only for patterns with historical admitted factors.

### Inputs

```text
attempt_count
admitted_count
high_quality_count
recent_attempt_count
recent_pass_count
recent_admitted_count
recent_p75_max_corr
historical_best_before_recent
recent_best_score
```

### Formula

```python
evidence = 1.0 - exp(-attempt_count / EVIDENCE_SCALE)
success_gate = 1.0 - exp(-admitted_count / SUCCESS_SCALE)
coverage = 1.0 - exp(-admitted_count / COVERAGE_SCALE)

corr_pressure = sigmoid((recent_p75_max_corr - CORR_THRESHOLD) / CORR_TEMP)

historical_novelty_yield = admitted_count / max(high_quality_count, 1)
recent_novelty_yield = recent_admitted_count / max(recent_pass_count, 1)
novelty_decay = sigmoid(
    (historical_novelty_yield - recent_novelty_yield - YIELD_MARGIN) / YIELD_TEMP
)

improvement = max(0.0, recent_best_score - historical_best_before_recent)
score_plateau = exp(-improvement / SCORE_DELTA)

diminishing_return = 0.5 * novelty_decay + 0.5 * score_plateau
core_saturation = corr_pressure * diminishing_return

saturation_score = evidence * success_gate * (
    0.75 * core_saturation
    + 0.25 * coverage * corr_pressure
)

saturation_score = clip(saturation_score)
```

### Interpretation

High `saturation_score` means:

```text
The pattern has worked before, but recent candidates are increasingly redundant and are not
improving the library much.
```

It does not mean the pattern is financially invalid. It means the nearby formula region is
crowded under the current library.

### Saturation Actions

```text
saturation_score < DEPRIORITIZE_THRESHOLD:
  Keep normal exploration.

DEPRIORITIZE_THRESHOLD <= saturation_score < RESTRICT_THRESHOLD:
  Deprioritize this pattern. Prefer lower-saturation directions.

RESTRICT_THRESHOLD <= saturation_score < FORBIDDEN_THRESHOLD:
  Explore only if the candidate introduces a clearly orthogonal information source.

saturation_score >= FORBIDDEN_THRESHOLD and minimum evidence requirements are satisfied:
  Move to forbidden_regions with reason = "saturated_high_corr".
```

Minimum evidence requirements for `saturated_high_corr`:

```python
attempt_count >= MIN_SATURATION_ATTEMPTS
admitted_count >= MIN_SATURATION_ADMITTED
recent_attempt_count >= MIN_RECENT_ATTEMPTS
recent_pass_count >= MIN_RECENT_PASS
```

These requirements prevent a pattern with only one admitted factor, or only one recent
high-correlation candidate, from being prematurely treated as saturated.

## Low Yield Score

Use low yield for patterns that have enough attempts but little evidence of effectiveness.
This is not a redundancy metric.

### Inputs

```text
attempt_count
pass_count
admitted_count
avg_score
```

### Formula

```python
evidence = 1.0 - exp(-attempt_count / EVIDENCE_SCALE)
no_success_gate = exp(-admitted_count / SUCCESS_SCALE)

pass_rate = (pass_count + 1.0) / (attempt_count + 2.0)
pass_failure = 1.0 - pass_rate

score_deficit = clip((PASS_THRESHOLD - avg_score) / PASS_THRESHOLD)

low_yield_score = evidence * no_success_gate * (
    0.65 * pass_failure
    + 0.35 * score_deficit
)

low_yield_score = clip(low_yield_score)
```

### Interpretation

High `low_yield_score` means:

```text
The pattern has been tried enough, rarely passes the score threshold, and has low average
score. It has not demonstrated enough promise.
```

If a pattern has admitted factors, `no_success_gate` suppresses low yield and the pattern
should usually be judged by saturation instead.

### Low Yield Actions

```text
low_yield_score < DEPRIORITIZE_THRESHOLD:
  Keep normal exploration.

DEPRIORITIZE_THRESHOLD <= low_yield_score < RESTRICT_THRESHOLD:
  Deprioritize this pattern.

RESTRICT_THRESHOLD <= low_yield_score < FORBIDDEN_THRESHOLD:
  Explore only after a major structural change.

low_yield_score >= FORBIDDEN_THRESHOLD and minimum evidence requirements are satisfied:
  Move to forbidden_regions with reason = "persistent_low_score".
```

Minimum evidence requirements for `persistent_low_score`:

```python
attempt_count >= MIN_LOW_YIELD_ATTEMPTS
admitted_count == 0
```

## Forbidden Region Format

Use explicit reasons and include evidence fields so future agents know why a direction was
forbidden.

```json
{
  "direction": "VWAP Deviation Variants",
  "reason": "saturated_high_corr",
  "evidence": {
    "saturation_score": 0.84,
    "low_yield_score": 0.12,
    "attempt_count": 32,
    "admitted_count": 5,
    "recent_p75_max_corr": 0.68,
    "recent_attempt_count": 20,
    "recent_admitted_count": 0,
    "recent_pass_count": 6
  }
}
```

```json
{
  "direction": "Noisy Microstructure Moment",
  "reason": "persistent_low_score",
  "evidence": {
    "saturation_score": 0.03,
    "low_yield_score": 0.86,
    "attempt_count": 24,
    "pass_count": 1,
    "admitted_count": 0,
    "avg_score": 8.7
  }
}
```

## Trajectory Log

To recompute metrics consistently, append one record per proposed candidate.

Recommended file:

```text
data/mining_trajectory.jsonl
```

This is the canonical storage location for all proposed factors and all evaluated factor
outcomes. Other files have narrower purposes:

```text
data/mining_trajectory.jsonl:
  Append-only log of every proposed candidate formula, its target patterns, evaluation result,
  correlation diagnostics, and final decision. Recent windows must be computed from this file.

data/factor_library.json:
  Only admitted library factors. Do not use it to reconstruct attempts or recent statistics.

data/experience_memory.json:
  Pattern summaries, forbidden regions, and computed diagnostics. Do not use it as the raw
  history of proposed formulas.
```

If a formula is proposed but not evaluated, still append a trajectory record with
`status = "proposed"` or `decision = "not_evaluated"` and leave score/correlation fields null.
Once evaluation finishes, update the record or append a final evaluated record with the same
`formula` and `candidate_id`. Implementations should prefer stable `candidate_id` values.

Recommended record shape:

```json
{
  "candidate_id": "iter3_007",
  "iteration": 3,
  "formula": "Cs_Rank(Ts_Std(Returns, 20))",
  "patterns": ["VolatilityReversal"],
  "status": "evaluated",
  "tot_score": 42.5,
  "verdict": "PASS",
  "decision": "duplicate_intra_batch",
  "max_corr": 0.64,
  "dup_corr": 0.61,
  "matched_factor": 12
}
```

Counting rules:

```text
attempt_count:
  Count every proposed or evaluated trajectory record for the pattern. If proposal-only records
  are later updated in place, count the candidate_id once.

pass_count and high_quality_count:
  Count records with tot_score >= PASS_THRESHOLD.

admitted_count:
  Count records whose final decision is admit or replace, after intra-batch duplicate rollback.

recent_p75_max_corr:
  Compute from recent records with tot_score >= PASS_THRESHOLD and available max_corr.
  If dup_corr is available but max_corr is missing, use dup_corr as a fallback for recent
  redundancy diagnostics.

recent_*:
  Sort records for each pattern by append order or timestamp, take the latest RECENT_WINDOW
  unique candidate_ids, and compute recent fields from that pattern-specific subset.
```

## Implementation Guidance

Prefer implementing the formulas in:

```text
scripts/memory/pattern_metrics.py
```

Recommended public functions:

```python
def compute_saturation(stats, params=None) -> float:
    ...


def compute_low_yield(stats, params=None) -> float:
    ...


def classify_pattern(stats, params=None) -> dict:
    ...
```

`classify_pattern` should return:

```python
{
    "saturation_score": 0.74,
    "low_yield_score": 0.18,
    "status": "deprioritize",
    "forbidden_reason": None,
}
```

or:

```python
{
    "saturation_score": 0.86,
    "low_yield_score": 0.09,
    "status": "forbidden",
    "forbidden_reason": "saturated_high_corr",
}
```

Suggested status rules:

```python
sat_forbidden = (
    saturation_score >= FORBIDDEN_THRESHOLD
    and attempt_count >= MIN_SATURATION_ATTEMPTS
    and admitted_count >= MIN_SATURATION_ADMITTED
    and recent_attempt_count >= MIN_RECENT_ATTEMPTS
    and recent_pass_count >= MIN_RECENT_PASS
)

low_yield_forbidden = (
    low_yield_score >= FORBIDDEN_THRESHOLD
    and attempt_count >= MIN_LOW_YIELD_ATTEMPTS
    and admitted_count == 0
)

if sat_forbidden:
    status = "forbidden"
    forbidden_reason = "saturated_high_corr"
elif low_yield_forbidden:
    status = "forbidden"
    forbidden_reason = "persistent_low_score"
elif max(saturation_score, low_yield_score) >= RESTRICT_THRESHOLD:
    status = "restricted"
    forbidden_reason = None
elif max(saturation_score, low_yield_score) >= DEPRIORITIZE_THRESHOLD:
    status = "deprioritize"
    forbidden_reason = None
else:
    status = "active"
    forbidden_reason = None
```

## Skill Update Guidance

When updating `SKILL.md`, keep it concise and point here for formulas.

Recommended text for the MiningState section:

```markdown
Each pattern tracks two diagnostics:

- `saturation_score`: for historically successful patterns whose local search space is
  becoming crowded. It rises when recent correlations increase, admitted yield declines,
  and best-score improvement plateaus.
- `low_yield_score`: for patterns with enough attempts but little evidence of effectiveness.
  It rises when pass rate is low and average score is far below threshold.

Do not treat low recent success rate alone as saturation. Saturation means "previously useful
but now crowded"; low yield means "not yet useful after enough attempts".

Before updating pattern states, use `references/pattern_state_metrics.md` or the helper
functions in `scripts/memory/pattern_metrics.py`. Do not invent alternative formulas.
```

Recommended text for memory evolution:

```markdown
Move patterns into `forbidden_regions` with explicit reasons:

- `saturation_score >= 0.70` plus minimum saturation evidence -> `reason = "saturated_high_corr"`
- `low_yield_score >= 0.70` plus minimum low-yield evidence -> `reason = "persistent_low_score"`

A saturated pattern may still be financially meaningful, but nearby variants are too
redundant. A low-yield pattern has not produced enough scoring power after sufficient
attempts.
```

Recommended text for candidate storage:

```markdown
Append every proposed candidate formula to `data/mining_trajectory.jsonl` with its target
patterns. After evaluation, record `tot_score`, `verdict`, correlation diagnostics, and final
decision. `recent` pattern statistics are computed from this trajectory log using a
pattern-level rolling window, not from the latest global iteration.
```

## Do Not

- Do not use low recent success rate alone as saturation.
- Do not mix persistent low score and high correlation into one undifferentiated forbidden
  reason.
- Do not move a pattern with `admitted_count == 0` to `saturated_high_corr`; use
  `persistent_low_score` if its low-yield score is high.
- Do not move a historically productive pattern to `persistent_low_score` unless the user
  explicitly asks to override the gate.
