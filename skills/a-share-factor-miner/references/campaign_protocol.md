# Blinded Factor-Mining Campaign Protocol

## Contents

1. Campaign identity and roles
2. Default campaign budget
3. Discovery feedback and rolling diagnostics
4. Freeze and validation rules
5. Library artifacts
6. Comparison matrix
7. Stop, failure, and restart rules

## 1. Campaign identity and roles

Treat a campaign as an immutable experiment identified by:

```text
campaign_version
data_snapshot
discovery_dates
factor_validation_dates
universe_version
label_version
evaluator_version
evaluator_freeze_hash
evaluator_score_config_hash
evaluator_controls_hash
evaluator_calibration_report_hash
operator_library_hash
pattern_state_hash
candidate_budget
visibility_policy
```

Create the campaign manifest before evaluating the first proposal.
The initializer must verify the frozen evaluator manifest and all bound artifact hashes. If the
score config, controls, calibration evidence, or evaluator implementation changes, refuse to
create the campaign and calibrate a new evaluator version.

Separate the roles:

- `generator`: may read operators, economic patterns, Red Sea/low-yield state, existing formulas,
  discovery diagnostics, and discovery-period correlations;
- `discovery_evaluator`: may read warm-up and discovery labels only;
- `factor_validator`: may read the frozen formula set and 2021-2022 labels only after freeze;
- `synthesis_evaluator`: may read 2023-2024 only after all factor libraries are frozen;
- `lockbox_evaluator`: may read 2025-latest once for the final report.

Do not return factor-validation or later metrics to the generator. If the current agent has seen
validation results from a previous campaign, use a fresh isolated context or subagent for new
formula generation. Give it only the campaign manifest, this skill, operator/pattern state, and
discovery artifacts. Shared filesystem access does not authorize reading validation result
directories; list the allowed paths in its task.

## 2. Default campaign and Pack-40 budget

Use these defaults unless the user changes them before the campaign starts:

```text
pack_size:                          40 unique proposals
internal_sub_batch_size:            10 proposals
candidate_budget:                  120 unique valid-or-invalid proposals
maximum_packs:                       3
minimum_packs_before_yield_stop:     2
minimum_economic_families:          8
target_frozen_candidates:       15-25
minimum_frozen_candidates:         12
target_predictive_core:           5-8 independent factors
target_tradable_core:             3-5 independent factors
comparison_ready_minimum:           8 predictive factors / 4 families
comparison_ready_target:        12-20 predictive factors
marginal_yield_window:               2 packs
minimum_new_survivors_in_window:     1
```

Targets guide search breadth; they never override hard gates. Do not manufacture factors or
weaken thresholds to meet a target.

Follow `factor_pack_protocol.md`: one user-visible run seals and evaluates 40 proposals as four
non-adaptive sub-batches of ten. The campaign normally contains three such packs. Load data once
per pack and update Red Sea state only after all 40 outcomes have been appended.

Cover at least eight structurally distinct economic families. Prefer underrepresented families
and cap the frozen set at three candidates per family or correlation cluster. Example families:

- overnight versus intraday decomposition;
- short-horizon price pressure and reversal;
- trend quality, path efficiency, and anchoring;
- price-volume or price-turnover disagreement;
- liquidity and trading-amount shocks;
- volatility level, change, and upside/downside asymmetry;
- return tails, skewness, and extreme-return preference;
- signed volume and accumulation/distribution pressure;
- range/location signals;
- conditional regimes or interactions.

Treat window perturbations and monotonic transforms as robustness variants, not independent
candidate mechanisms.

## 3. Discovery feedback and rolling diagnostics

Use 2015 only for warm-up. During generation, expose only 2016-2020 diagnostics.

For each candidate, report:

- formula/panel validity and coverage;
- full-discovery raw and neutralized Rank IC;
- direction fixed from the pre-registered discovery rule;
- expanding or rolling subperiod IC signs, worst subperiod, and hit rate;
- discovery-only transaction-cost diagnostics;
- parameter-free status and planned perturbation family;
- canonical, rank-equivalent, batch, family, and existing-library correlations;
- economic gate and target patterns.

Use discovery cost to distinguish likely predictive-only signals from implementation candidates.
Do not reject a statistically useful signal solely because a daily long-short implementation is
costly. Do reject formulas that are invalid, degenerate, duplicative, or economically `FAIL`.

Discovery survivor labels are provisional:

- `discovery_research`: independent discovery IC in `[0.005, 0.01)` with coherent economics;
- `discovery_qualified`: discovery neutralized IC at least `0.01` with stable subperiod signs;
- `discovery_implementation`: discovery-qualified and positive under the declared 10 bps test;
- `discovery_fail`, `duplicate`, or `invalid` otherwise.

These labels do not constitute admission and must not be written to the formal core library.

## 4. Freeze and validation rules

Stop generation when any pre-registered condition fires:

1. the 120-candidate or three-pack budget is reached;
2. after at least two packs, two consecutive packs produce no new independent
   `discovery_research` or `discovery_qualified` survivor at average absolute daily Spearman
   correlation below `0.50`;
3. the declared compute budget is exhausted;
4. all permitted patterns are restricted or forbidden by valid Red Sea/low-yield evidence.

Before factor validation:

1. greedily deduplicate by daily cross-sectional correlation and economic family;
2. retain at most three candidates per family/cluster;
3. freeze formulas, directions, parameter perturbations, data/evaluator identities, FDR history,
   and the formula-set hash;
4. aim for 15-25 candidates and require at least 12 by default.

The proposal manifest and parameter plan for each pack must be sealed before that pack sees any
discovery labels. Parameter variants created after discovery are diagnostic only and invalidate
formal preregistration for the affected candidate.

The freeze command must receive an immutable parameter-plan JSON covering every
discovery-eligible candidate, not only the candidates eventually retained by global deduplication.
Each entry must declare either `parameter_free: true` or a non-empty, named formula-variant list.
Persist the parameter-plan hash in the formula-freeze manifest. The factor validator must refuse
to open validation when this hash or plan is missing or changed. If validation was opened without
this artifact, mark the campaign `audit_blocked_missing_preregistered_parameter_plan`; post-hoc
variants may be reported as diagnostics but can never repair formal admission for that campaign.

If fewer than 12 independent candidates remain, label the campaign `insufficient_yield`. Do not
lower gates. The user may explicitly authorize validating the smaller frozen set, or start a new
campaign that expands operators, fields, or economic families.

Open 2021-2022 once for the entire frozen set. Apply direction from discovery. Do not generate,
modify, or replace formulas after viewing validation results under the campaign version.
Parameter perturbations, holding/smoothing diagnostics, transfers, and cost stress are allowed
only when pre-declared and must not change the base formula or direction.

Apply validation FDR over the global history of unique production candidates tested under the
compatible evaluator version. Never compute FDR only over survivors.

## 5. Library artifacts

Persist five separate versioned artifacts:

1. `candidate_trajectory`: every proposal, including invalid, failed, and duplicate formulas;
2. `research_library`: economically coherent factors worth monitoring, including independent
   IC in `[0.005, 0.01)` and qualified signals with implementation concerns;
3. `predictive_core_library`: deduplicated local factors passing formula, statistical,
   robustness, economic, FDR, and qualified-score gates; transaction cost remains scored but is
   not a universal hard gate because this library feeds model synthesis;
4. `tradable_core_library`: predictive-core factors that also have positive 10 bps net Sharpe,
   non-negative 20 bps net Sharpe, acceptable turnover, and a documented execution convention;
5. `benchmark_control_library`: frozen legacy FactorMiner factors, classic factors,
   representative Alpha158 factors, random/noise controls, and invalid controls.

The local factor library contains only locally researched factors. Do not admit benchmarks,
Alpha158, random controls, or invalid controls into it. Do not delete failed or superseded factors
from the trajectory.

## 6. Comparison matrix

After factor libraries are frozen, compare on identical point-in-time samples, labels, rolling
splits, neutralization, costs, and portfolio rules:

```text
A: local predictive core only
B: local tradable core only
C: legacy FactorMiner library
D: Alpha158 benchmark library
E: local predictive core + Alpha158
F: fixed classic factors
```

Report individual-factor IC/ICIR and correlations before model comparison. For LightGBM,
XGBoost, and Ridge, compare Rank IC, ICIR, yearly stability, group monotonicity, long-short
returns, turnover, cost stress, and feature importance/stability. Use 2023-2024 only for this
synthesis comparison and 2025-latest only once as the final lockbox.

Do not make comparison easier by retaining only successful local factors while silently dropping
failed attempts. Report candidate counts, rejection reasons, family yields, and global FDR.

Do not begin the headline local-vs-Alpha158 comparison with fewer than 8 formally qualified,
deduplicated local predictive factors across at least 4 families. Prefer 12-20. Also report the
full Alpha158 library and a label-blind equal-count Alpha158 subset so library size is not a hidden
advantage. Provisional candidates may be used only for pipeline rehearsal and must be labeled so.

## 7. Stop, failure, and restart rules

A campaign is complete when its formula set and library decisions are frozen, even if it misses
the target number of factors. Quality targets are aspirations, not guaranteed outputs.

After factor validation is opened:

- do not resume that campaign's generator;
- do not use its validation metrics to design nearby formulas in another nominal version;
- start a genuinely isolated campaign with pre-registered families and discovery-only feedback;
- preserve prior validation outcomes for global FDR and audit, but keep them hidden from the new
  generator.

If repeated price-volume campaigns remain low yield, expand the observable information domain
under a new evaluator version, for example point-in-time valuation, quality, growth, analyst, or
fundamental fields. Do not mine synthesis-validation or lockbox periods to compensate for low
yield.
