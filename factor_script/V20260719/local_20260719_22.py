"""Twenty-day overnight drift relative to intraday drift."""

FACTOR_NAME = "local_20260719_22"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Sub(Ts_Mean(Div(Sub(open, pre_close), pre_close), 20, 10), Ts_Mean(Div(Sub(close, open), open), 20, 10)))"
ECONOMIC_HYPOTHESIS = "A persistent overnight premium unsupported by intraday trading is more likely to reflect segmentation or price pressure."
TARGET_PATTERNS = "OvernightIntradayDecomposition"
