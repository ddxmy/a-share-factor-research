# Factor Pack-40 Protocol

## Purpose

A single skill run must yield one auditable pack of 40 unique proposals rather than one formula
at a time. Pack-40 improves throughput without weakening blindness, preregistration, or global
multiple-testing correction.

## Fixed shape

```text
pack_size:                  40 proposals
internal_sub_batches:        4
proposals_per_sub_batch:    10
campaign_size:               3 packs / 120 proposals
discovery_panel_loads:       1 per pack
pattern_state_updates:       1 after the full pack
```

Every proposal counts against the budget, including invalid formulas and exact duplicates. A
replacement formula created after linting is a new proposal; it cannot reuse the rejected ID.

## Before evaluation

Create a proposal manifest containing exactly 40 records. Each record must include:

```text
candidate_id
factor_name
formula
economic_hypothesis
economic_family
data_domain
target_patterns
internal_sub_batch (1-4)
```

The four sub-batches must each contain exactly ten records. Generate them for structural coverage,
not sequential feedback; no record in the pack may use another record's discovery metrics.

Create the parameter-plan JSON at the same time. It must cover every candidate ID and declare
either `parameter_free: true` or a non-empty named `formula_variants` list. Seal both artifacts
with `scripts/init_factor_pack.py` before linting or evaluation.

The sealed pack manifest must also bind the hashes of `scripts/prepare_factor_pack.py`,
`scripts/finalize_factor_pack.py`, and the discovery evaluator. Refuse to materialize, evaluate,
or finalize a pack if its bound implementation changes after sealing.

## Domain allocation

Use only domains marked `enabled` in `references/data_domains_v1.json` and bound into the campaign
manifest. Default allocation for the current market-data-only lake is:

```text
price/path/range:                 10
volume/amount/turnover/liquidity: 10
volatility/tails/asymmetry:        8
overnight/intraday decomposition:  6
cross-domain interactions:         6
```

After point-in-time valuation, financial, and money-flow domains pass their data audits, replace
at least 16 of the 40 market-only slots with those domains. Do not label a planned domain enabled
merely because Tushare exposes an endpoint.

## Execution

1. Lint all 40 without labels. The lint must include expression-shape inference: a formula must
   return a date-security panel, and the true branch of `If(condition, x, y)` must be panel-valued
   because the local runtime dispatches `x.where(condition, y)`. Scalar/scalar branches are
   invalid even when their AST and operator arity are otherwise legal.
2. Load the frozen discovery panel once.
3. Evaluate all valid formulas in one process; failures remain in the trajectory.
4. Apply discovery-only canonical and panel deduplication globally across the pack and history.
5. Write one pack report and compact candidate table. Do not persist rejected panels.
6. Append all 40 stable records to the candidate trajectory.
7. Recompute pack-level attempt, yield, and correlation state once after the full append. If
   complete formal quality scores do not yet exist, record Red Sea classification as deferred;
   discovery tiers must never be substituted for formal Red Sea pass/admission statistics.

## Required pack artifacts

```text
pack_manifest.json
proposals.json
parameter_plan.json
lint_results.csv
discovery_metrics.csv
pack_summary.md
trajectory_append.jsonl
pattern_state_after_pack.json
```

The summary must report proposal, invalid, duplicate, discovery-research, discovery-qualified,
independent-survivor, family-yield, and data-domain-yield counts. It must not contain factor-
validation, transfer, synthesis-validation, or lockbox labels.

## Campaign transition

Run up to three Pack-40s under a 120-proposal campaign. Formula generation stops before opening
factor validation. After all 120 outcomes are present, run
`scripts/consolidate_campaign_parameter_plans.py` to mechanically combine the three sealed
per-pack parameter plans. Then run `local_research/formal_pipeline/freeze_pack_campaign.py` once
with that immutable 120-record plan to recompute cross-pack discovery correlations and greedily
freeze 12-25 candidates using the pre-registered 0.50 correlation threshold and per-family cap.
This global pass may replace or reject pack-local survivors; pack-local selection is diagnostic
only. Freeze candidates and their sealed parameter plans exactly as specified in
`campaign_protocol.md` before opening 2021-2022 labels. A Pack-40 is a throughput unit, not an
admission unit: zero, one, or many members may survive, and none enters an active core library
before all formal gates pass.
