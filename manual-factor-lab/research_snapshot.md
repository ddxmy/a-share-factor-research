# CSI 300 Daily Factor Research Snapshot

## Research question

This study asks whether a small, economically motivated set of daily A-share
signals can rank subsequent cross-sectional excess returns after point-in-time
universe construction and leakage-aware timing. It is a single-factor screen,
not a claim that any factor is independently investable.

## Fixed research design

| Component | Choice |
| --- | --- |
| Universe | Point-in-time CSI 300 constituents on each signal date |
| Signal timing | Values use observations available through the signal-date close |
| Execution label | Entry at the next trading-day open; 1D, 5D, and 20D open-to-open excess-return labels |
| Formal evaluation period | 2021--2025; 2026 is reserved as a blind period |
| Primary statistic | Daily cross-sectional Spearman Rank IC, direction-aligned to the pre-registered hypothesis |
| Inference | Bartlett Newey--West HAC standard errors with horizon-aware overlap treatment |
| Cross-sectional treatment | Median imputation, MAD winsorization, and Z-score standardization after raw-factor calculation |
| Portfolio diagnostic | Equal-weight Top-30 and quintile portfolios at matched 1D, 5D, and 20D holding periods; 10 bps one-way cost assumption |

The explicit timing convention is `Close[t] -> Open[t+1] -> Open[t+h+1]`.
No formula callable receives future labels, entry data, or tradability flags.
Missing terminal observations remain missing rather than being converted into
zero returns.

## Candidate set

The initial library contains ten frozen formulas. Each module returns only
`trade_date`, `security_id`, and raw factor values; direction handling,
outlier treatment, labels, and portfolio construction occur in shared code.

| Family | Factors | Economic interpretation |
| --- | --- | --- |
| Return continuation and reversal | REV5, MOM20, MOM60 | Recent price movement may reverse or continue over different horizons. |
| Risk | VOL20, IDIOVOL20 | Realized and residual volatility proxy for risk, limits to arbitrage, or lottery demand. |
| Trading activity and liquidity | TURN20, VOLSURP20, AMIHUD20 | Attention, information arrival, and trading frictions may affect subsequent returns. |
| Price-volume structure | PV_CORR20, CLOSE_POS5 | Demand persistence can appear in price-volume co-movement or closing location. |

Formula definitions, required fields, expected direction, and availability are
frozen in [factor_registry.csv](factor_registry.csv). The implementations are
kept one factor per file in [factors/](factors/), making each candidate easy to
review and replace without changing the evaluation engine.

## Evidence and decision boundary

The engine produces immutable private run bundles containing data-quality
checks, daily IC series, HAC summaries, annual stability summaries, and
matched-horizon portfolio diagnostics. The public repository intentionally
excludes these outputs because it does not distribute the licensed input data.

An implementation-complete factor is not automatically an admitted factor.
The formal decision rule requires sufficient eligible observations, positive
direction-aligned 1D Rank IC, one-sided HAC significance, positive evidence in
at least four calendar years, and a positive next-open-tradable IC diagnostic.
Portfolio results remain diagnostic until suspension handling, price-limit
constraints, delayed exits, and benchmark total-return consistency have been
audited under a trading specification.

## Reproduce locally

Provide the four private Parquet inputs described in
[README.md](README.md), then run:

```bash
A_SHARE_DATA_ROOT='<private-data-root>' python -m a_share_factor_research.main \
  --factor IDIOVOL20 \
  --profile manual-factor-lab/config/daily_baseline.yaml \
  --start 2021-01-01 \
  --end 2025-12-31
```

The command publishes a self-contained private run directory beneath
`A_SHARE_DATA_ROOT/runs/`. Public tests verify the formula, data-timing, label,
evaluation, portfolio, and output-boundary contracts without requiring market
data.
