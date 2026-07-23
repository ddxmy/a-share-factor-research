# Formal local factor pipeline

Build a frozen point-in-time HS300 input panel through factor validation only:

```bash
/opt/miniconda3/bin/python3 -B local_research/formal_pipeline/build_input_panel.py
```

Run all active non-retired factor scripts:

```bash
/opt/miniconda3/bin/python3 -B local_research/formal_pipeline/evaluate_factors.py \
  --panel /absolute/path/to/panel-20150101-20221231-factor_validation-*.parquet
```

The builder binds the data-quality snapshot, dynamic universe, point-in-time SW2021 industry
intervals, log float market capitalization, and next-open-to-close labels. The evaluator uses
2016-2020 for direction discovery and 2021-2022 for factor validation. It does not open later
stages unless a separate stage-specific input is explicitly built.

The primary evaluator performs daily 1%/99% winsorization, equal-weight industry and log-float-cap
neutralization, residual z-scoring, Rank IC, Newey-West tests, BH-FDR, quantile portfolios, and
10/20 bps cost stress. Results remain non-admissible until transfer universes, parameter
perturbations, library correlations, and economic review are complete.
