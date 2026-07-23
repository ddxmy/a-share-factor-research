---
name: factor-mining-experiment
description: Automated T-1 factor mining using Ralph Loop - self-evolving factor discovery with run_factor + FactorTest evaluation.

Use when user wants to:
  - Mine factors / automatically discover factors / batch generate factors
  - Run Ralph Loop / factor mining loop
  - Discover novel alpha factors
  - Build factor library
  - Evaluate a single factor formula

Data required: parquet with columns (dt, Ticker, open, high, low, close, volume, amt, vwap, pre_close, pct_chg, ...)
---

## Overview

This skill implements **Algorithm 1: Ralph Loop** — an automated T-1 factor discovery system
with experience memory. **Claude (you) acts as the LLM**, generating factors, analyzing results,
and updating memory directly. The only external tool is `run_factor` + `FactorTest` (Python 3.8
compiled modules) for evaluation.

### Core Components

| Component                    | Description                                                         |
| :--------------------------- | :------------------------------------------------------------------ |
| **Ω (Operator Library)**     | 82 vectorized financial operators with exact pandas/numpy formulas |
| **M (Experience Memory)**    | Success patterns + Forbidden Regions distilled from tot_score results |
| **L (Factor Library)**       | Admitted factors with factor_name / formula / tot_score             |
| **π (Generator)**            | **Claude** generates factors using operator library + memory        |
| **Evaluator**                | `run_factor` + `FactorTest` via py38 subprocess → tot_score (0–100) |

## Evaluation Metric

The system uses **run_factor + FactorTest** (compiled .so modules) to score each factor on a 0–100 scale. A factor is judged along two dimensions:

- **Discrimination** — after controlling for limit-up time, does the factor independently separate winners from losers?
- **Stability** — does the factor-label correlation persist consistently across months?

### Pass Condition

| Verdict   | Condition           |
| :-------- | :------------------ |
| **PASS**  | tot_score >= **30** |
| **FAIL**  | tot_score <  **30** |

### Data Preprocessing

Before computing factor values, market data undergoes the same preprocessing as all europa
hand-written factors:

1. **Adjustment factor normalization** — multiply open/close/high/low/vwap by adjfactor
2. **Registration-based board normalization** — ChiNext (300-xxx, >=20200824) and STAR (688-xxx) price limits are ±20%
   rather than ±10%. Prices are re-scaled to make pct_chg calculations consistent across all stocks.

These are applied automatically in `_load_market_data()` (evaluator.py).

## Ralph Loop (Claude executes this loop)

### Step 1: Read Current State

```bash
# Read operator library
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py operators

# Read experience memory (success patterns with MiningState + forbidden regions)
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py memory-read

# Read factor library (already admitted factors)
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py library-read
```

- **Cold start (empty memory):** No prior patterns exist. Draw on your quantitative finance
  knowledge to encourage broad, diverse exploration across the full operator library.
  No preset direction bias — do not prematurely narrow the search.
- **Warm state:** 
  - Use success patterns to guide generation, avoid forbidden regions
  - **Prioritize patterns with LOW scores** (both saturation_score and low_yield_score < 0.45)
  - **Deprioritize** patterns with scores in [0.45, 0.60)
  - **Restrict** patterns with scores in [0.60, 0.70) — explore only with clearly orthogonal candidates
  - **Avoid** patterns with scores ≥ 0.70 (these should be auto-moved to forbidden_regions)
  - Don't duplicate already-admitted factor structures

**MiningState Interpretation:**

Each success pattern tracks **two distinct failure modes**:

1. **`saturation_score` (0-1)**: Pattern was historically useful, but its local search space is now crowded.
   - Rises when: recent correlations increase, admitted yield declines, best-score improvement plateaus
   - High score means: "previously productive but now overpopulated"
   - Formula structure: `evidence × success_gate × (0.75·core_saturation + 0.25·coverage·corr_pressure)`
     - `corr_pressure` = sigmoid of (recent_p75_max_corr - CORR_THRESHOLD)
     - `core_saturation` = `corr_pressure × diminishing_return`
     - `diminishing_return` = 0.5·novelty_decay + 0.5·score_plateau

2. **`low_yield_score` (0-1)**: Pattern has enough attempts but little evidence of effectiveness.
   - Rises when: pass rate is low, average score far below threshold
   - High score means: "not yet useful after enough attempts"
   - Formula structure: `evidence × no_success_gate × (0.65·pass_failure + 0.35·score_deficit)`
     - `no_success_gate` = exp(-admitted_count / SUCCESS_SCALE) → suppresses if pattern has admitted factors

**⚠️ Do NOT treat low recent success rate alone as saturation.** Saturation = "previously useful but now crowded"; low yield = "not yet useful after enough attempts".

**Shared fields per pattern:**
- `attempt_count`: Total candidates attempted
- `pass_count` / `high_quality_count`: Candidates with score ≥ PASS_THRESHOLD
- `admitted_count`: Candidates admitted to library (decision ∈ {admit, replace} after intra-batch dedup)
- `avg_score`: Historical average score over all attempts
- `best_score`: Historical best score
- `recent_*`: Computed from pattern-level rolling window (latest 20 candidates by default)
  - `recent_attempt_count`, `recent_pass_count`, `recent_admitted_count`
  - `recent_p75_max_corr`: 75th percentile of recent high-quality candidates' max |corr| with library
  - `recent_best_score`: Best score within recent window

**Action thresholds (both metrics):**
- `< 0.45` (DEPRIORITIZE_THRESHOLD): Normal exploration
- `0.45 – 0.60` (RESTRICT_THRESHOLD): Deprioritize, prefer lower-score directions
- `0.60 – 0.70` (FORBIDDEN_THRESHOLD): Explore only if candidate introduces clearly orthogonal information
- `≥ 0.70` + minimum evidence → move to `forbidden_regions`

**Minimum evidence requirements:**
- For `saturated_high_corr`: attempt_count ≥ 16, admitted_count ≥ 3, recent_attempt_count ≥ 5, recent_pass_count ≥ 2
- For `persistent_low_score`: attempt_count ≥ 16, admitted_count == 0

**Do NOT:**
- Mix persistent low score and high correlation into one undifferentiated forbidden reason
- Move a pattern with `admitted_count == 0` to `saturated_high_corr`; use `persistent_low_score` if low_yield is high
- Move a historically productive pattern to `persistent_low_score` unless user explicitly overrides

> Complete formulas, all intermediate variables, default parameters, and exact `recent` window definition: see `scripts/references/pattern_state_metrics.md`.

**Legacy fields** (kept for backward compatibility):
- `factor_count`: Number of factors in library matching this pattern
- `recent_success_rate`: Success rate in last iteration
- `avg_correlation`: Mean pairwise |corr| among pattern factors

### Step 2: Generate Factors

**You (Claude) generate ~10 diverse factor formulas directly.**

Guidelines:
- Use ONLY operators from the operator library (read in Step 1)
- Follow success patterns, avoid forbidden regions
- Don't duplicate already-admitted factor structures
- Aim for 2–5 nested operator depth
- Freely choose from ANY operator categories — do NOT restrict yourself to a subset
- Each formula must be interpretable — another quant should understand the economic intuition

**Systematic Pattern Matching (REQUIRED):**

After generating formulas, you MUST systematically match each formula against ALL success patterns in the experience memory (from Step 1):

1. **For each formula**, iterate through every pattern in `success_patterns`
2. **Check if the formula embodies that pattern's economic concept** based on the pattern's description
3. **A formula can match multiple patterns** — list ALL matches
4. **If a formula matches no existing pattern**, mark it as `targets: []` (exploring new direction)

**Matching criteria:**
- Does the formula use operators/logic that capture the pattern's described economic phenomenon?
- Does the formula's structure align with the pattern's mechanism?
- Is the formula's financial intuition consistent with the pattern's concept?

**Output format (REQUIRED):**

First, list all formulas:
```
1. Cs_Rank(Ts_Std(close, 20))
2. Ts_EMA(Div(Returns, amt), 12)
3. If(Or(Greater(Abs(Ts_Skewness(Returns,24)),1.5), Greater(Ts_Kurtosis(Returns,24),4.0)), Neg(Ts_Residual(close,vwap,6)), Neg(Ts_Rank(Returns,24)))
4. Sub(close, vwap)
...
```

Then, provide a **pattern matching table** showing systematic matching:

```
Pattern Matching:
  Formula 1: targets [VolatilityAdjustedSkewness]
    - VolatilityAdjustedSkewness: YES (Ts_Std captures volatility, division adjusts skewness)
    - SmoothedEfficiency: NO
    - HigherMomentRegimes: NO
    ...
  
  Formula 2: targets [SmoothedEfficiency]
    - VolatilityAdjustedSkewness: NO
    - SmoothedEfficiency: YES (EMA smoothing applied to Returns/Amt efficiency)
    - HigherMomentRegimes: NO
    ...
  
  Formula 3: targets [HigherMomentRegimes, TrendRegressionAdaptive, LogicalOrExtremes]
    - VolatilityAdjustedSkewness: NO
    - SmoothedEfficiency: NO
    - HigherMomentRegimes: YES (uses Skew/Kurt in If condition)
    - TrendRegressionAdaptive: YES (Ts_Residual for regression residual)
    - LogicalOrExtremes: YES (Or operator for extreme conditions)
    ...
  
  Formula 4: targets []
    - VolatilityAdjustedSkewness: NO
    - SmoothedEfficiency: NO
    - HigherMomentRegimes: NO
    - TrendRegressionAdaptive: NO
    - LogicalOrExtremes: NO
    (exploring new direction)
```

**Multi-pattern factors**: Each pattern in the targets list counts independently for that pattern's success rate in Step 4. The matching table makes your reasoning explicit and auditable.

### Step 3: Evaluate Factors

```bash
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py eval "formula1" "formula2" ... "formula10"
```

**Evaluation Process (report-only, does NOT auto-admit to library):**
1. **Score Evaluation**: Each factor is scored via run_factor + FactorTest (tot_score 0–100)
2. **Library Correlation Check**: Factors that pass (score ≥ 30) are checked against existing library factors
3. **Intra-batch Dedup**: Among factors that would be admitted from step 2, check pairwise correlation within the batch

**Library Correlation Logic** (step 2, for factors with score ≥ 30):
- Compute Spearman |correlation| with all existing library factors
- Let g★ = argmax_{g∈L} |ρ(α, g)| (the best-matched library factor)
- If |ρ(α, g★)| ≥ 0.5 (high correlation with best match):
  - **Condition 1**: |ρ(α, g★)| ≥ 0.5 ✓ (already satisfied)
  - **Condition 2**: max_{g∈L\{g★}} |ρ(α, g)| < 0.5 (low correlation with ALL OTHER library factors)
  - **Condition 3**: score(α) > score(g★) (higher score than best match)
  - If ALL 3 conditions met → **replace** g★ with α (should replace old factor)
  - Otherwise → **reject** (keep existing factors)
- If |ρ(α, g★)| < 0.5 (low correlation with all) → **admit** (should be added to library)

**Note**: The 3-condition replacement logic ensures that a new factor not only beats its best match but also doesn't conflict with other library factors. This prevents replacing a factor when the new one would create redundancy elsewhere in the library.

**Intra-batch Dedup Logic** (step 3, for factors with decision ∈ {admit, replace}):
- Sort all surviving candidates by tot_score descending
- Greedy iterate: for each candidate, check Spearman |corr| against all already-kept candidates
  - Any |corr| ≥ 0.5 → **duplicate_intra_batch** (report which kept factor it duplicates)
  - All |corr| < 0.5 → keep and add to the kept set

Example — A(55), B(42), C(38) with corr(A,C)=0.62, corr(C,B)=0.58, corr(A,B)=0.31:
```
A → kept
B → corr(B,A)=0.31 < 0.5 → kept
C → corr(C,A)=0.62 ≥ 0.5 → duplicate of A
Result: A and B should be admitted
```

**Output JSON:**

```json
[
  {
    "formula": "...",
    "factor_name": "...",
    "tot_score": 55.2,
    "verdict": "PASS",
    "max_corr": 0.32,
    "matched_factor": null,
    "decision": "admit"
  },
  {
    "formula": "...",
    "factor_name": "...",
    "tot_score": 42.0,
    "verdict": "PASS",
    "max_corr": 0.20,
    "matched_factor": null,
    "decision": "duplicate_intra_batch",
    "dup_of": "...",
    "dup_corr": 0.62
  },
  {
    "formula": "...",
    "factor_name": "...",
    "tot_score": 12.8,
    "verdict": "FAIL",
    "decision": "skip_score_fail"
  }
]
```

**Decision Types:**
- `admit`: Low correlation with library → **Claude should call library-add to admit**
- `replace`: High correlation with library factor but higher score → **Claude should call library-remove then library-add**
- `reject`: High correlation with library factor and lower score → not admitted
- `duplicate_intra_batch`: High correlation with another batch factor (lower score) → not admitted
- `skip_score_fail`: Score below threshold, no correlation check → not admitted
- `panel_error`: Failed to compute factor panel for correlation check → not admitted

**Optional Flags:**
- `--no-corr`: Skip correlation check, only score evaluation
- `--corr-threshold 0.6`: Change correlation threshold (default: 0.5)

### Step 4: Analyze Results & Update MiningState

> **Hard rule — before any MiningState update:** You MUST re-read `scripts/references/pattern_state_metrics.md` for the authoritative formulas, weights, and thresholds. Do NOT invent or approximate alternative formulas from memory.

> **Trajectory log:** Every proposed and evaluated candidate MUST be appended to `data/mining_trajectory.jsonl` (one JSON object per candidate). The `recent` window used in `saturation_score` and `low_yield_score` is computed from this log at the pattern level (rolling window per pattern, not global). See `scripts/references/pattern_state_metrics.md` for exact log format and window definition.

**You (Claude) analyze the evaluation results and update pattern states:**

#### 4a. Calculate Success Rates per Pattern

Use the pattern annotations from Step 2 to calculate success rates:

1. **Group formulas by their annotated target patterns** (from Step 2).
   A formula with `targets: [A, B, C]` counts toward patterns A, B, and C independently.
2. **For each pattern that had formulas targeting it**, count:
   - `total_count`: how many formulas included this pattern in their targets list
   - `passed_count`: how many of those got verdict=PASS
   - `recent_success_rate = passed_count / total_count`

3. **Formulas annotated with "targets: []"** (empty list, exploring new direction):
   - **PASS**: candidates for **new pattern extraction** (see 4d below)
   - **FAIL**: discard — do NOT extract forbidden regions from failures

**Note**: Even formulas that targeted existing patterns can contain new pattern insights (see 4d).

#### 4b. Update MiningState for Targeted Patterns

For each success pattern that had formulas targeting it in this iteration, compute the new state:

```python
factor_count = len(library_factors_matching_this_pattern)  # current count in library
recent_success_rate = passed_count / total_count           # this iteration's rate
avg_correlation = mean_pairwise_spearman_corr              # among all library factors for this pattern
```

**Update the pattern state:**

```bash
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py memory-update \
  --update-state '[
    {"pattern":"SmoothedEfficiency", "factor_count":3, "recent_success_rate":0.5, "avg_correlation":0.42},
    {"pattern":"HighR2TrendFollowing", "factor_count":2, "recent_success_rate":0.33, "avg_correlation":0.61}
  ]'
```

#### 4c. Memory Evolution (auto-promote saturated patterns)

Run evolution to move patterns that exceed thresholds **and** satisfy minimum evidence requirements to forbidden_regions:

```bash
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py memory-update --evolve
```

This automatically:
- Identifies success patterns with `saturation_score >= 0.7` **and** minimum evidence (attempt_count ≥ 16, admitted_count ≥ 3, recent_attempt_count ≥ 5, recent_pass_count ≥ 2) → removed with reason `saturated_high_corr`
- Identifies success patterns with `low_yield_score >= 0.7` **and** minimum evidence (attempt_count ≥ 16, admitted_count == 0) → removed with reason `persistent_low_score`
- Moves matched patterns to `forbidden_regions` (each entry records its removal reason and evidence fields)
- Removes them from `success_patterns`

**Interpretation**: Saturated or persistently low-yield patterns are no longer productive exploration
targets. They are "forbidden" not because they are fundamentally flawed, but because further
exploration in that direction is unlikely to yield novel factors.

#### 4d. Extract New Patterns from Admitted Formulas

Analyze **only admitted formulas** (those with `decision=admit` or `decision=replace` that you called `library-add` for) to discover **new** success patterns. An admitted formula that matches existing patterns may still reveal a different economic insight worth capturing as a separate pattern.

> **Before extracting patterns, re-read the existing memory** (Step 1 output) and compare
> each candidate pattern against it. Only pass patterns that are **genuinely new** — do NOT
> pass a pattern that is semantically equivalent to one already stored (same idea, different
> wording). `memory-update` **appends** to existing patterns; duplicates are never removed
> automatically, so deduplication is your responsibility.

**Important**: Do NOT extract new patterns from formulas that were rejected, failed score, or were deduplicated — only from formulas that actually entered the library.

**Pattern Extraction: Economic Concept, Not Formula Description**

A pattern must describe the **economic concept / financial intuition** behind successful
factors. The name should tell you *what economic phenomenon* the pattern captures, not
*which variables or operators* were used.

**Naming principles:**

1. **Name = Economic concept** — The pattern name should be a short phrase (2-5 words) that
   captures the financial intuition. It can include:
   - Fields with economic meaning (VWAP, R², Efficiency = Returns/Amt)
   - Operations with financial intuition (Standardized, Reversion, Trend Following, Smoothed)
   - Regimes or conditions (High R², Extreme, Dual Horizon)

2. **Description = one sentence** — A concise sentence (1-2 lines) that states:
   - What operators/concepts are used (the mechanism)
   - What financial phenomenon it captures (the intuition)
   - No need to enumerate operator slots or list variants

   **Good descriptions (from reference patterns):**
   - "Use Skew/Kurt as IfElse conditions to identify extreme asymmetric or fat-tail environments for reversal signals."
   - "Combine price-volume correlation (Corr) with amount efficiency or trend operators to capture volume-price coordination."
   - "Use median (Med) and other robust statistics to smooth amount efficiency, filtering extreme noise."
   - "Apply time-series smoothing (EMA) to amount efficiency before cross-sectional ranking."
   - "Use Rsquare/Slope/Resi operators for adaptive trend regression. High R2 → slope reversal; Low R2 → residual reversal."

   **Bad descriptions:**
   - "Core: Cs_Rank(Inverse(Disp(x,d))/Loc(x,d)). Disp∈{Std,MAD}, Loc∈{Mean,Median}, d∈{10,20,60}. Logic: ... Variants: formula1, formula2." ← too verbose, reads like a spec sheet

**Examples of good vs bad pattern names:**

| ❌ Bad (formula/variable description) | ✅ Good (economic concept) |
|---|---|
| `TurnoverStabilityPremium` | `LiquidityStability` — turn represents liquidity, stability is the economic concept |
| `MultiTimescaleTurnoverStability` | `DualHorizonLiquidity` — dual timescale is the key insight |
| `ConcavePowerTurnoverPenalty` | *(merge into LiquidityStability — just a different Location estimate)* |
| `ReturnsDivAmtInteraction` | `Standardized Efficiency` — Returns/Amt = Efficiency (a fixed economic concept), standardized = the operation |
| `RsquareConditionalMomentum` | `High R² Trend Following` — R² regime + trend following intuition |
| `WeightedMomentumByRsquare` | `R² Weighted Momentum` — R² as confidence weight |
| `EMAOfReturnsDivAmt` | `Smoothed Efficiency` — EMA smoothing applied to Efficiency concept |
| `CloseMinusVWAP` | `VWAP Deviation` — deviation from VWAP is the economic concept |
| `ClosePositionInHighLowRange` | `Close-Position Location` — position within range is the concept |
| `TsDeltaNegation` | `Simple Delta Reversal` — reversal is the financial intuition |

**Anti-patterns to avoid:**
- If 3+ formulas share the same structure with only variable/window/operator swaps, they are
  **one pattern with variants**, not 3 separate patterns.
- Never name a pattern by just describing the formula (e.g., `InverseStdOverMean`).
- Never name a pattern by just listing variables (e.g., `CloseVolumeCorrelation`).
- If an operator combination forms a well-known economic concept (VWAP Deviation, Amount
  Efficiency = Returns/Amt, Liquidity = turnover), use that concept directly in the name —
  don't "translate" it into a more abstract term.

**Add new patterns (only for genuinely novel PASS formulas):**

```bash
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py memory-update \
  --success '[
    {"pattern":"VolatilityAdjustedSkewness", "description":"Divide time-series skewness by rolling volatility to capture asymmetry per unit of risk.", "mining_state":{"factor_count":1, "recent_success_rate":1.0, "avg_correlation":0.0}}
  ]'
```

#### 4e. Manually Admit Factors to Library

**Important**: `eval` is report-only and does not auto-admit factors to the library.
Use the `decision` field in the eval output to decide when to call `library-add` manually.
`library-add` is the only persistence entry point for admitted factors: it updates
`data/factor_library.json`, writes the runnable Python factor script under
`factor_script/V<current_date>/`, and keeps the factor's `run_factor` evaluation artifacts under
`tmp_data/V<current_date>_factor_<factor_id>_<factor_name>/`.

**Factor naming:** Each factor must have a meaningful `factor_name` that captures its economic concept, not the formula itself. Use the same naming principles as pattern extraction:
- Name should reflect the economic intuition (e.g., `Trend_Reliability_Switch_V2`)
- Avoid formula descriptions (e.g., `IfElse_Greater_Rsquare_Neg_Slope`)
- Keep it concise (2-5 words) and interpretable

**For factors with decision=admit:**
```bash
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py library-add \
  "Trend_Reliability_Switch_V2" \
  "If(Greater(Ts_Rsquare(close, vwap, 24), 0.75), Neg(Slope(close, 12)), Neg(Ts_Rank(Returns, 12)))" \
  55.2
```
This writes:
- `data/factor_library.json`: metadata record with `factor_id`, `factor_name`, `formula`, `tot_score`
- `factor_script/V<current_date>/factor_<factor_id>_<factor_name>.py`: generated europa-style T-1 factor script
- `tmp_data/V<current_date>_factor_<factor_id>_<factor_name>/`: retained `run_factor` evaluation artifacts, including `.pq` files

**For factors with decision=replace:**
1. First remove the old factor using `library-remove <replaced_factor_id>` (from `replaced_factor` field in eval output)
2. Then add the new factor using `library-add` with your chosen economic concept name.
   `library-remove` also removes the old generated script from `factor_script/`.

**For factors with decision=reject or duplicate_intra_batch:**
- Do nothing (these factors are not admitted to the library)

**Summary of Step 4:**
1. Group formulas by their Step 2 pattern annotations, calculate success rates per pattern
2. For each targeted pattern, compute `factor_count`, `recent_success_rate`, `avg_correlation`
3. Update pattern states with `--update-state`
4. Run `--evolve` to move saturated patterns (≥0.7) to forbidden_regions
5. Analyze **all PASS formulas** to extract **new** patterns (not just those annotated with "targets: none")
6. **Manually admit factors**: For each factor with `decision=admit` or `decision=replace`, call `library-add` with a meaningful economic concept name

**Parameter change constraint:** Thresholds, weights, and windows (e.g., saturation threshold, low_yield threshold, rolling window size) may be tuned per experiment. However, parameters MUST NOT be silently modified. If any parameter is changed, you MUST first update `scripts/references/pattern_state_metrics.md` to reflect the new value and record the reason for the change.

### Step 5: Check Stopping Conditions

- **Target reached**: 50 newly discovered factors (or user-specified target)
- **Max iterations**: 10 iterations (or user-specified max)

If neither condition is met, go back to Step 1 and repeat.

## Usage

### Full Ralph Loop

Claude executes the 5-step loop above. The user can specify:
- Target number of factors (default: 50)
- Maximum iterations (default: 10)
- Batch size per iteration (default: 10)
- Pass threshold (default: 30.0)

### Single Factor Evaluation

```bash
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py eval "Cs_Rank(Div(Ts_Skewness(Ts_ZScore(close,20),20), Ts_Std(Ts_ZScore(close,20),20)))"
```

### Fresh Start

```bash
# Clear memory and library
python /workspace/user_homes/xiezutian/factor_mining/factor-mining-experiment/scripts/main.py reset
```

## Persistent State

```
data/
├── factor_library.json        # [{factor_name, formula, tot_score}, ...]
├── experience_memory.json     # {success_patterns: [...], forbidden_regions: [...]}
└── mining_trajectory.jsonl    # Append-only log of every proposed/evaluated candidate
factor_script/
└── V<current_date>/factor_<factor_id>_<factor_name>.py  # generated scripts for admitted factors
tmp_data/
└── V<current_date>_factor_<factor_id>_<factor_name>/    # ignored evaluation artifacts
```

**Trajectory log record format (one per candidate):**

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

If a formula is proposed but not evaluated, append with `status = "proposed"` and leave score/correlation fields null. The `recent` window for saturation_score and low_yield_score is computed from this log at the **pattern level** (rolling window of latest 20 candidates per pattern, not global iteration).

**FactorRecord format:**

```json
{
  "factor_name": "Cs_Rank_Neg_Ts_ZScore_close_20_",
  "formula": "Cs_Rank(Neg(Ts_ZScore(close, 20)))",
  "tot_score": 72.5
}
```

**Success Pattern format (with MiningState):**

```json
{
  "pattern": "VolatilityAdjustedSkewness",
  "description": "Divide time-series skewness of returns by its own rolling volatility to capture asymmetry per unit of risk, then cross-sectionally rank.",
  "mining_state": {
    "factor_count": 3,
    "recent_success_rate": 0.5,
    "avg_correlation": 0.42,
    "saturation_score": 0.456,
    "low_yield_score": 0.20,
    "attempt_count": 24,
    "pass_count": 11,
    "high_quality_count": 11,
    "admitted_count": 3,
    "avg_score": 38.7,
    "best_score": 55.2,
    "recent_attempt_count": 12,
    "recent_pass_count": 4,
    "recent_high_quality_count": 4,
    "recent_admitted_count": 1,
    "recent_p75_max_corr": 0.52,
    "historical_best_before_recent": 55.2,
    "recent_best_score": 48.3
  }
}
```

**Forbidden Region format (with explicit reason and evidence):**

```json
{
  "direction": "VWAPDeviationVariants",
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
  "direction": "NoisyMicrostructureMoment",
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

Note: Forbidden regions are created automatically when success patterns exceed threshold (≥0.7) **and** satisfy minimum evidence requirements. Each entry records its removal reason and supporting evidence fields.

Plain `eval` uses a temporary `/tmp/factor_eval_*` result directory and auto-cleans it after
reporting scores. `library-add` re-runs the admitted formula with a persistent result directory
under `tmp_data/V<current_date>_factor_<factor_id>_<factor_name>/`, so the admitted factor's
`.pq` files are retained there. `tmp_data/` is git-ignored; `factor_script/` is intended to be
committed.

### Operator Library Categories

| Category | Count | Key Operators |
|----------|-------|---------------|
| TimeSeries | 28 | Ts_Rank, Ts_Return, Ts_ZScore, Ts_EMA, Ts_Std, Ts_ArgMax, Ts_DecayLinear, ... |
| CrossSectional | 10 | Cs_Rank, Cs_ZScore, Cs_Median, Cs_Winsorize, ... |
| Math | 16 | Add, Sub, Mul, Div, SignedPower, Inverse, Neg, ... |
| Financial | 12 | open, close, high, low, pre_close, vwap, volume, amt, pct_chg, Returns, change, turn |
| Logical | 7 | If, Greater, Less, And, Or, Not, Equal |
| Statistical | 9 | MACD, RSI, BBands_Upper/Lower, VWAP_Deviation, Slope, Volatility_Ratio, ... |
