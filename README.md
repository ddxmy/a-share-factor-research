# A-Share Factor Research

This repository publishes compact, data-free implementations for two
point-in-time CSI 300 research workflows: an Alpha158 model experiment and a
manual single-factor laboratory. It contains source code, frozen methodology,
selected figures, and tests; it deliberately does not contain market data,
derived panels, run artifacts, or notebooks.

## Research snapshot

| Track | Research question | Primary evidence | Public entry point |
| --- | --- | --- | --- |
| Alpha158 | Can a fixed Alpha158 feature set rank next-week CSI 300 excess returns out of sample? | Purged rolling folds, neutralized Rank IC, and a cost-sensitive Top-50 diagnostic | [Alpha158 experiment](alpha158/README.md) |
| Manual factors | Do economically motivated daily signals retain direction-consistent cross-sectional ranking ability under a fixed PIT protocol? | Formula contracts, daily Rank IC/HAC evaluation, and matched holding-period diagnostics | [Manual-factor snapshot](manual-factor-lab/research_snapshot.md) |

The repository is designed as a research artifact rather than a strategy
claim. Signals are formed with information through the close and evaluated
from the next open; results remain sensitive to the data vendor, point-in-time
universe reconstruction, and execution assumptions.

The Alpha158 experiment is documented in [alpha158/README.md](alpha158/README.md).
The manual factor workflow is documented in
[manual-factor-lab/README.md](manual-factor-lab/README.md). Private inputs
must be supplied through `A_SHARE_DATA_ROOT`; see
[alpha158/config/data_root.example](alpha158/config/data_root.example) and
[manual-factor-lab/config/daily_baseline.yaml](manual-factor-lab/config/daily_baseline.yaml).

Published results are historical research diagnostics, not investment advice
or evidence of deployable performance.
