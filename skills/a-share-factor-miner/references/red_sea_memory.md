# Red Sea and Low-Yield Memory

## Purpose

Preserve the original FactorMiner search-space evolution while replacing legacy `tot_score`
with the local quality score.

Keep two separate diagnoses:

- `saturation_score` (Red Sea): the pattern worked before, but nearby candidates have become
  crowded, redundant, and unable to improve the library;
- `low_yield_score`: the pattern has enough attempts but rarely demonstrates effectiveness.

Never infer Red Sea status merely from a low recent success rate.

## Canonical parameters

```python
PASS_THRESHOLD = 65.0
CORR_THRESHOLD = 0.50
EVIDENCE_SCALE = 8.0
SUCCESS_SCALE = 1.5
COVERAGE_SCALE = 4.0
CORR_TEMP = 0.05
YIELD_MARGIN = 0.15
YIELD_TEMP = 0.10
SCORE_DELTA = 5.0
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

Compared with the legacy protocol, preserve the nonlinear structure and evidence requirements.
Change only the pass threshold from legacy 30 to local qualified 65 and the meaningful score
improvement from 3 to 5 points. Keep the original 0.50 correlation center.

## Shared statistics

Compute statistics from unique candidate IDs in the append-only trajectory:

```text
attempt_count
pass_count: complete quality score >= 65 and all required gates passed
admitted_count: final decision in {admit, replace}
avg_score: complete quality scores; provisional scores do not count
best_score
recent_attempt_count
recent_pass_count
recent_admitted_count
recent_p75_max_corr
historical_best_before_recent
recent_best_score
```

Use the latest 20 candidates for each pattern, never the latest global iteration.

## Red Sea formula

```python
evidence = 1 - exp(-attempt_count / EVIDENCE_SCALE)
success_gate = 1 - exp(-admitted_count / SUCCESS_SCALE)
coverage = 1 - exp(-admitted_count / COVERAGE_SCALE)

corr_pressure = sigmoid((recent_p75_max_corr - CORR_THRESHOLD) / CORR_TEMP)

historical_novelty_yield = admitted_count / max(pass_count, 1)
recent_novelty_yield = recent_admitted_count / max(recent_pass_count, 1)
novelty_decay = sigmoid(
    (historical_novelty_yield - recent_novelty_yield - YIELD_MARGIN) / YIELD_TEMP
)

improvement = max(0, recent_best_score - historical_best_before_recent)
score_plateau = exp(-improvement / SCORE_DELTA)
diminishing_return = 0.5 * novelty_decay + 0.5 * score_plateau
core_saturation = corr_pressure * diminishing_return

saturation_score = clip(
    evidence * success_gate * (
        0.75 * core_saturation + 0.25 * coverage * corr_pressure
    )
)
```

Move a pattern to forbidden regions with legacy-compatible reason
`saturated_high_corr` only when:

```text
saturation_score >= 0.70
attempt_count >= 16
admitted_count >= 3
recent_attempt_count >= 5
recent_pass_count >= 2
```

Record `red_sea: true` in its evidence for clarity. A Red Sea pattern remains economically
meaningful; the local formula neighbourhood is simply exhausted.

## Low-yield formula

```python
evidence = 1 - exp(-attempt_count / EVIDENCE_SCALE)
no_success_gate = exp(-admitted_count / SUCCESS_SCALE)
pass_rate = (pass_count + 1) / (attempt_count + 2)
pass_failure = 1 - pass_rate
score_deficit = clip((PASS_THRESHOLD - avg_score) / PASS_THRESHOLD)

low_yield_score = clip(
    evidence * no_success_gate * (
        0.65 * pass_failure + 0.35 * score_deficit
    )
)
```

Move a pattern with reason `persistent_low_score` only when:

```text
low_yield_score >= 0.70
attempt_count >= 16
admitted_count == 0
```

## Actions

```text
max score < 0.45: normal exploration
0.45 <= max score < 0.60: deprioritize
0.60 <= max score < 0.70: restrict; require structural novelty
score >= 0.70 plus evidence: forbidden under the explicit reason
```

Do not compute Red Sea or low-yield evolution from provisional calibration scores. Begin local
memory evolution only after the complete evaluator version is frozen.
