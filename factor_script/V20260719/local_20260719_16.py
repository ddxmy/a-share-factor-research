"""Persistent overnight return component."""

FACTOR_NAME = "local_20260719_16"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Div(Sub(open, pre_close), pre_close), 20, 10))"
ECONOMIC_HYPOTHESIS = "A persistent overnight component may capture slow incorporation of information arriving outside trading hours."
TARGET_PATTERNS = "OvernightDrift"
