# FactorMiner

Self-evolving agent for automated T-1 alpha factor discovery — implements **Algorithm 1:
Ralph Loop** with experience memory.

Factors are evaluated via `run_factor` + `FactorTest` (same pipeline used by all
hand-written europa factors at Baihai), with automatic adjfactor (复权) and
registration-system price-limit correction (注册制修正).

## Architecture

```
                     ┌────────────────────┐
                     │  Ω  Operator Lib    │  60+ vectorised financial operators
                     └────────┬───────────┘
                              │
   ┌──────────┐     ┌────────▼────────┐     ┌──────────────┐
   │  Memory  │────▶│  π  Generator   │────▶│  Evaluator   │
   │  M + L   │ m_t │  (LLM-guided)   │  C  │  run_factor  │
   └────▲─────┘     └─────────────────┘     │  +FactorTest │
        │                                   └──────┬───────┘
        │              ┌──────────┐                 │
        └──────────────│  Memory  │◀────────────────┘
                       │  Update  │  scores / verdicts
                       └──────────┘
```

### Algorithm (5 Steps)

| Step | Name | Description |
|------|------|-------------|
| 1 | **Memory Retrieval** | Distil success patterns + forbidden regions into strategic guidance `m_t` |
| 2 | **Guided Generation** | LLM generates candidate formulas using operator library Ω, guided by `m_t` |
| 3 | **Evaluation** | `run_factor.so` → `test_factor_demo.so` via Python 3.8 subprocess → `tot_score` (0–100) |
| 4 | **Library Update** | Admit factors with `tot_score ≥ 30` into the factor library |
| 5 | **Memory Evolution** | Extract success patterns & forbidden regions from batch results, merge into `M_{t+1}` |

### Core Components

| Component | Description |
|-----------|-------------|
| **Ω (Operator Library)** | 60+ vectorised financial operators — rolling, cross-sectional, math, composite |
| **M (Experience Memory)** | Success patterns (named strategies) + Forbidden Regions (dead-end directions) |
| **L (Factor Library)** | Admitted factors with formula + tot_score |
| **π (Generator)** | LLM-based factor generation guided by memory signal |
| **Evaluator** | `run_factor` + `FactorTest` via Python 3.8 subprocess |

## Evaluation Metric

The system uses **run_factor + FactorTest** (compiled .so modules) to score each factor on a 0–100 scale. A factor is judged along two dimensions:

- **Discrimination** — after controlling for limit-up time, does the factor independently separate winners from losers?
- **Stability** — does the factor-label correlation persist consistently across months?

**Pass threshold:** `tot_score >= 30`

### Data Preprocessing

1. **adjfactor (复权)** — multiply ohlcv/vwap/pre_close by adjfactor
2. **注册制修正** — re-scale ChiNext (300-xxx, ≥20200824) and STAR (688-xxx) ±20%
   price limits to ±10% scale for pct_chg consistency

## File Layout

```
.
├── run_europa_factor.py                # (Legacy) europa factor runner
├── run_factor.so                       # C extension: factor data pipeline
├── test_factor_demo.so                 # C extension: FactorTest scoring
├── scripts/
│   ├── main.py                         # CLI entry (Ralph Loop + single-factor mode)
│   ├── loop/ralph_loop.py              # Core orchestrator (5-step loop)
│   ├── generation/factor_generator.py  # LLM → candidate formulas
│   ├── evaluation/
│   │   ├── evaluator.py                # tot_score eval via py38 subprocess
│   │   └── run_factor_eval.py          # py38 subprocess script
│   ├── memory/
│   │   ├── memory_store.py             # FactorLibrary + ExperienceMemory data model
│   │   ├── memory_retrieval.py         # Step 1: memory → guidance
│   │   ├── memory_formation.py         # Step 4: results → patterns
│   │   └── memory_evolution.py         # Step 5: merge old + new memory
│   ├── operators/operator_library.py   # 60+ financial operators (Ω)
│   ├── llm/llm_client.py               # OpenAI-compatible API client
│   └── utils/config.py                 # Global configuration
├── marketdata/                         # Trading-day helper + data interface
├── factor_framework/europa/            # Hand-written europa factor definitions
└── data/
    ├── factor_library.json             # Admitted factor records
    └── experience_memory.json          # Success patterns + forbidden regions
```

## Requirements

### Orchestrator (Python ≥ 3.10)

```bash
pip install -r requirements.txt
```

### Evaluation Subprocess (Python 3.8)

The evaluation pipeline (`run_factor.so` + `test_factor_demo.so`) requires a separate
conda environment:

```bash
conda create -n py38 python=3.8
conda activate py38
pip install numpy==1.24.4 pandas==2.0.3
```

The `.so` modules must be on `PYTHONPATH`.

### Data Files

| File | Path |
|------|------|
| Market data (parquet) | `/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq` |
| Basic sample data | `/workspace/public/data/project/basic_data/20160101_20181231.pq` |

### Environment

```bash
export FM_API_KEY="sk-xxx"                  # LLM API key (required)
export FM_BASE_URL="http://172.16.1.203:4000"  # LLM API endpoint (optional)
```

## Usage

### Full Ralph Loop

```bash
cd scripts

# Default run (target 50 factors, max 10 iterations)
python main.py

# Custom parameters
python main.py --target 100 --max-iters 20 --batch-size 15 --threshold 30

# Fresh start (clear memory & library)
python main.py --reset
```

### Single Factor Evaluation

```bash
python main.py --factor-name "Cs_Rank(Inverse(Ts_Std(Returns, 20)))"
# → {"factor_name": "...", "tot_score": 52.2, "verdict": "PASS"}
```

### Custom Evaluation Function

```bash
python main.py --eval-fn mymodule.eval:my_custom_eval
```

## Persistent State

```
data/
├── factor_library.json        # [{factor_name, formula, tot_score}, ...]
└── experience_memory.json     # {success_patterns: [...], forbidden_regions: [...]}
```

- **FactorRecord:** `{factor_name, formula, tot_score}`
- **Success Pattern:** `{pattern: "CamelCaseName", description: "...", category: "success"}`
- **Forbidden Region:** `{direction: "CamelCaseName", category: "forbidden"}`
