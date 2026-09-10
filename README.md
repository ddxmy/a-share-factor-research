# A-Share Factor Research

This repository publishes compact, data-free implementations for two
point-in-time CSI 300 research workflows: an Alpha158 model experiment and a
manual single-factor laboratory. It contains source code, frozen methodology,
selected figures, and tests; it deliberately does not contain market data,
derived panels, run artifacts, or notebooks.

The Alpha158 experiment is documented in [alpha158/README.md](alpha158/README.md).
The manual factor workflow is documented in
[manual-factor-lab/README.md](manual-factor-lab/README.md). Private inputs
must be supplied through `A_SHARE_DATA_ROOT`; see
[alpha158/config/data_root.example](alpha158/config/data_root.example) and
[manual-factor-lab/config/daily_baseline.yaml](manual-factor-lab/config/daily_baseline.yaml).

Published results are historical research diagnostics, not investment advice
or evidence of deployable performance.
