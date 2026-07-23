"""Five-day smoothed overnight-versus-intraday disagreement."""

FACTOR_NAME = "local_20260719_11"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Sub(Div(Sub(close, open), open), Div(Sub(open, pre_close), pre_close)), 5, 3))"
ECONOMIC_HYPOTHESIS = "Persistent disagreement between overnight and intraday returns is less likely to be one-day microstructure noise."
TARGET_PATTERNS = "OvernightIntradayDecomposition"
