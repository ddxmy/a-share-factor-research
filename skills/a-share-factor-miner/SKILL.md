---
name: a-share-factor-miner
description: Run blinded multi-batch discovery, linting, neutralized evaluation, deduplication, admission, Red Sea evolution, and benchmark comparison for daily A-share formulaic factors. Use for local FactorMiner/Ralph campaigns, factor-library construction, score calibration, single-factor review, or preparation of local factors for Alpha158 and machine-learning synthesis.
---

# A-Share Factor Miner

Run reproducible local Ralph campaigns. Let the LLM propose economic hypotheses and interpret
discovery evidence; delegate execution, scoring, multiple testing, correlation checks, and state
updates to deterministic scripts. Accumulate a diversified library rather than stopping after
the first successful factor.

## Required references

- Before scoring or changing thresholds, read `references/evaluation_protocol.md` and
  `references/quality_score_v1.json` completely.
- Before calibrating the evaluator or auditing its freeze, read
  `references/calibration_controls_v1.json` and `references/evaluator_freeze_v1.json`
  completely.
- Before starting, resuming, freezing, or validating a mining campaign, read
  `references/campaign_protocol.md` completely.
- Before generating a 40-factor run, read `references/factor_pack_protocol.md` completely.
- Before downloading, joining, or validating data, read `references/data_contract.md`.
- Before changing pattern state or forbidden regions, read `references/red_sea_memory.md`
  completely. Do not approximate its formulas from memory.

## Non-negotiable research rules

1. Use point-in-time universes, industries, security status, and tradability masks.
2. Use only information observable by the factor timestamp.
3. Set factor direction from the discovery sample and freeze it everywhere else.
4. Keep the generator blind to factor-validation, synthesis-validation, transfer, and lockbox
   labels until the campaign formula set is frozen.
5. Apply hard gates before the quality score. A high score never overrides a failed hard gate.
6. Store raw metrics and score components; never treat one scalar as sufficient evidence.
7. Append every proposal and outcome to the trajectory log, including invalid and rejected factors.
8. Never change scoring thresholds silently. Create a new evaluator version and record why.
9. Do not persist all candidate panels. Persist admitted panels and compact diagnostics only.
10. Do not delete or replace legacy FactorMiner state during local research.
11. Never resume formula generation under a campaign after opening its factor-validation labels.
12. Keep local factors, legacy factors, Alpha158 factors, and calibration controls in separate
    versioned libraries so comparisons do not alter admission or deduplication decisions.
13. Treat `data/libraries/library_index.json` as the only active-library entry point. A script's
    presence under `factor_script/` is trajectory evidence, not library membership.

## Default research protocol

Use the following dates after the full 2015-to-present data lake is ready:

| Segment | Dates | Visibility |
|---|---|---|
| Warm-up | 2015 | Features only; do not score |
| Discovery | 2016-2020 | Visible to the generator and evaluator |
| Factor validation | 2021-2022 | Hidden from generator; opened once after campaign freeze |
| Synthesis validation | 2023-2024 | Open only after the factor library is frozen |
| Final lockbox | 2025-latest completed day | Open once for the final report |

Use dynamic CSI 300 as the primary universe. Use CSI 500 and point-in-time liquid all-A only as
transfer checks. Use next-day open-to-close return as the primary label; keep next
close-to-close as a secondary diagnostic shared by FactorMiner and Alpha158.

## Campaign workflow

### 1. Pre-register and read state

Read the operator library, admitted library, experience memory, trajectory log, evaluator
version, data snapshot, and current Red Sea/low-yield pattern status.

Create an immutable campaign manifest before generating formulas. Bind its discovery dates,
candidate budget, batch size, economic-family coverage, stop rules, data snapshot, evaluator
version, and visibility policy. Use the defaults in `references/campaign_protocol.md` unless the
user explicitly changes them before the first candidate is evaluated.

Initialize the manifest with `scripts/init_campaign.py`; it refuses to overwrite an existing
campaign identity. Record any user-authorized deviation in the manifest rather than editing it
after evaluation begins.

Prioritize active patterns. Deprioritize or restrict patterns as directed by
`references/red_sea_memory.md`. A Red Sea pattern may be economically valid but locally
exhausted; a low-yield pattern has not demonstrated enough effectiveness.

### 2. Generate one Factor Pack

One skill invocation produces one sealed Factor Pack of exactly 40 proposals. Internally organize
it as four structural sub-batches of ten so generation remains diverse, but load the discovery
panel once and evaluate all 40 in one deterministic evaluator process. Follow
`references/factor_pack_protocol.md`.

Before any proposal sees a discovery label, seal the 40 formulas and the parameter plan covering
all 40. For each formula:

- state the economic mechanism;
- match it against every existing pattern;
- list all target patterns or use an empty list for a new direction;
- use only registered operators and observable fields;
- prefer structural diversity over window or monotonic-transform variants.

Return one pack-level report plus only discovery-period diagnostics to the generator. Do not expose factor-validation,
transfer, synthesis-validation, or lockbox metrics during batch iteration. If the active agent
has already seen validation outcomes that could steer a new campaign, use a fresh isolated
generator context or subagent that receives only the skill, pre-registered manifest, operator
library, pattern state, formulas, and discovery artifacts. Do not pass validation results.

### 3. Lint before backtesting

Reject formulas that are invalid, forward-looking, scalar-valued, constant, insufficiently
cross-sectional, dimensionally incoherent, dominated by division-by-zero, or canonically
equivalent to an existing proposal. Detect monotonic rank equivalence where practical.

### 4. Screen on discovery without persistence

Compute raw and industry/log-float-cap-neutralized signals. Apply winsorization, neutralization,
and z-scoring using only each date's cross-section. During formula generation, evaluate only the
discovery period and its pre-registered rolling subperiod diagnostics.

Return formula/panel gates, discovery IC and stability, transaction-cost diagnostics, canonical
deduplication, and discovery-period library correlations. Treat cost as a score and library-tier
input, not a universal predictive-signal hard gate. Persist compact diagnostics, not candidate
panels.

### 5. Stop and freeze before validation

Continue batches until a pre-registered budget or marginal-yield rule fires. Do not stop merely
because one factor succeeds. Aim for the diversified freeze targets in
`references/campaign_protocol.md`; never relax quality gates to fill a quota.

Freeze formula hashes, directions, parameter grids, evaluator version, data snapshot, candidate
history, family assignments, and the library/campaign hash. Require the deterministic freeze tool
to hash an immutable parameter plan covering every discovery-eligible candidate; the validator
must refuse to run if the plan is absent or changed. If the minimum diversified freeze set is not
reached, label the campaign `insufficient_yield`; either stop or expand the operator or data domain
under a new campaign version.

### 6. Validate the frozen set once

Only after freeze, open factor-validation labels and evaluate the complete frozen set in one
run. Then compute hard-gate diagnostics, Newey-West statistics, global candidate-history FDR,
raw metrics, quality-score components, transaction-cost stress, pre-declared parameter
perturbations, CSI 500 and liquid-all-A transfers, and library correlations. Freeze discovery
directions everywhere. Evaluation remains report-only.

### 7. Decide library placement

Use the rules in `references/evaluation_protocol.md`:

- `invalid`: failed formula/data gate;
- `fail`: valid formula but failed statistical or robustness gates;
- `research`: useful enough to retain for observation, not core synthesis;
- `admit`: passed every required gate and the qualified score threshold;
- `replace`: correlated with one library factor and materially better under the replacement rules;
- `duplicate`: redundant with a retained factor;
- `watchlist`: incomplete evidence or conditional economic interpretation.

Maintain the artifacts defined in `references/campaign_protocol.md`:

- an append-only candidate trajectory;
- a broad research library;
- a deduplicated predictive core for synthesis;
- a stricter tradable core for standalone portfolio claims;
- a frozen benchmark/control library kept separate from local admissions.

Persist an admitted local factor only after explicitly confirming its economic name, formula,
frozen direction, score version, data snapshot, correlation cluster, audit status, and library
role. A statistically strong high-turnover signal may enter predictive core while remaining
outside tradable core.

### 8. Update trajectory and memory

Append a stable candidate record containing formula hash, targets, status, all metrics, hard-gate
failures, score components, FDR q-value, correlations, economic tags, final decision, evaluator
version, and data snapshot.

Update pattern statistics from unique candidate IDs. Apply the Red Sea and low-yield formulas
from `references/red_sea_memory.md`; keep their reasons separate. Append all 40 outcomes, then
update pattern state once per pack so within-pack ordering cannot steer the remaining proposals.

### 9. Freeze the library for synthesis

Freeze research, predictive-core, tradable-core, and benchmark-library hashes before opening
synthesis validation. Compare local predictive core, Alpha158, legacy FactorMiner, and their
pre-registered combinations on the same labels and rolling splits. Never resume formula mining
after inspecting synthesis-validation or lockbox results under the same experiment version.

The minimum viable local-vs-Alpha158 comparison requires 8 formally qualified, deduplicated
predictive-core factors from at least 4 economic families. The preferred comparison library is
12-20 independent factors; 3-5 of them should also qualify for tradable core. Compare the full
Alpha158 set, an equal-count Alpha158 subset selected without synthesis labels, local-only, and
Alpha158-plus-local. Do not fill the quota by weakening gates.

## Frozen evaluator calibration

`hs300_daily_evaluator_v1` is frozen for new campaigns. Its thresholds were not changed during
calibration. The fixed suite contains classic controls, a representative Alpha158 subset,
deterministic noise, and invalid/leakage controls. Controls remain outside candidate-history FDR
and all active factor libraries. Reproduce or audit the freeze with:

```bash
python skills/a-share-factor-miner/scripts/run_evaluator_calibration.py \
  --hs300-panel <hs300-factor-validation-panel> \
  --csi500-panel <csi500-factor-validation-panel> \
  --liquid-all-a-panel <liquid-all-a-factor-validation-panel> \
  --output-dir <project>/local_research/results/evaluator_calibration_v1_20260722 \
  --resume
```

The freeze evidence is bound in `references/evaluator_freeze_v1.json`. A future threshold,
metric, label, neutralization, universe, or gate change requires a new evaluator version and a
fresh fixed-control calibration; never edit v1 thresholds in place. The representative Alpha158
subset is only a calibration anchor and does not replace the later full Alpha158 comparison.
