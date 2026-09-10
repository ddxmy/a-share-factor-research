# Manual Factor Laboratory

This directory is a researcher-owned laboratory for ten frozen daily factors.
It provides a reusable point-in-time evaluation engine while keeping licensed
data and generated research artifacts private. The ten formulas in
[`factors/`](factors/) are independently importable and each returns only
`trade_date`, `security_id`, and an untransformed `raw_value`. The legacy
functions in [`src/factors.py`](src/factors.py) remain as compatibility
bridges.

The immutable candidate list, field contract, availability rule, hypothesis,
and direction are in [factor_registry.csv](factor_registry.csv). The evaluation
and admission rules are in [research_protocol.md](research_protocol.md).

## Private data contract

Set `A_SHARE_DATA_ROOT` to an existing private directory containing exactly
these catalog inputs:

```text
derived/daily_panel.parquet
derived/universe/pit_csi300.parquet
derived/benchmark/csi300_open.parquet
derived/tradability/open_eligibility.parquet
```

The engine validates the factor ID, required daily fields, all catalog paths,
and the output boundary before it calls a factor formula. Every output is
confined below `A_SHARE_DATA_ROOT`; the default layout is
`runs/<factor_id>/<run_id>/` beneath that root. `--output-root`, when supplied,
must resolve exactly to `A_SHARE_DATA_ROOT/runs`: this guarantees every
successful command run can enter the private comparison records.

For a requested signal window, the engine loads the registered factor's
explicit pre-start trailing-session buffer and a benchmark-calendar forward
buffer through the largest requested horizon plus entry open. A factor callable
receives only signal-time fields through the requested end date: it never sees
entry dates, forward labels, label-derived eligibility, or next-open
tradability. After labels are attached, all IC, portfolio, NAV, and report rows
are clipped back to the requested signal-date window. Missing terminal catalog
coverage remains missing evidence; it is never treated as a zero return or a
valid observation.

## Public command

After installing the repository requirements, run a registered factor from the
repository root:

```bash
A_SHARE_DATA_ROOT='<private-data-root>' python -m a_share_factor_research.main \
  --factor REV5 \
  --profile manual-factor-lab/config/daily_baseline.yaml \
  --start 2021-01-01 \
  --end 2025-12-31
```

Each successful run is published atomically with:

```text
summary.json
data_quality.csv
ic_summary.csv
ic_daily.csv
portfolio_summary.csv
nav.csv
figures/cumulative_rank_ic.png
figures/annual_ic.png
figures/top_k_nav.png
report.html
```

`summary.json` records the frozen registry row, resolved profile, SHA-256 for
the profile, registry, and four catalog inputs, plus the Git revision when the
workspace is a Git checkout. The report keeps basic and tradable IC distinct
and compares gross/net Top-K NAV on independently matched 1D/5D/20D holding
profiles.

## Private performance records

The private output root separates immutable run evidence from derived local
comparison views:

- `runs/<factor_id>/<run_id>/` is the complete immutable evidence bundle for
  one factor run. The final run directory is published atomically before any
  comparison record is attempted.
- `factor_scoreboard.parquet` is the append-only comparison table derived only
  from validated, completely published runs. A duplicate `(factor_id, run_id)`
  is rejected rather than replaced. It includes comparable mean Top-K turnover
  for each matched 1D/5D/20D holding profile.
- `factor_scoreboard.duckdb` is the transactionally refreshed DuckDB mirror;
  its `factor_scoreboard` table contains the same records as the Parquet view.
- `factor_cards/<factor_id>.html` is the latest-success card for each factor,
  selected only from formal runs by recorded creation time with a deterministic
  run-ID tie-break.

The scoreboard, DuckDB mirror, and cards become visible together through one
atomic generation switch. If report publication fails, no scoreboard state is
created. If performance recording fails after publication, the complete run
directory remains unchanged and the command raises the recording error clearly.
The frozen `manual-factor-lab/config/daily_baseline.yaml` profile records
`run_type: formal`. Any other profile path records `run_type: experimental`;
experimental rows remain in the append-only scoreboard and DuckDB mirror but
never replace a factor's formal card. Use the default canonical output root for
ordinary research runs.

From `A_SHARE_DATA_ROOT`, DuckDB can query the local Parquet scoreboard
directly:

```sql
SELECT factor_id, run_type, decision, mean_rank_ic_1d,
       top_k_net_sharpe_5d, top_k_mean_turnover_5d
FROM read_parquet('factor_scoreboard.parquet')
ORDER BY created_at DESC;
```

## Research state

The initial formula set is implementation-complete: REV5, MOM20, MOM60,
VOL20, IDIOVOL20, TURN20, VOLSURP20, AMIHUD20, PV_CORR20, and CLOSE_POS5.
Their economic hypotheses and pre-registered directions are intentionally
separate from their observed performance. Formula status in the registry means
only that a tested implementation exists; it is never rewritten by a backtest.

The frozen formal screen uses daily point-in-time CSI 300 cross sections from
2021--2025, close-to-next-open signal availability, 1D/5D/20D open-to-open
excess-return labels, and direction-aligned Rank IC as the primary statistic.
Portfolio outputs are diagnostic evidence only. A production trading claim
would additionally require explicit treatment of suspensions, price limits,
delayed exits, and a total-return-consistent benchmark.

Run all public contract tests with:

```bash
python -m pytest manual-factor-lab/tests -v
```

No daily market data, derived panels, generated research results, or private
notebooks belong in this public laboratory.
