"""Signed directional efficiency of the recent price path."""

FACTOR_NAME = "local_20260719_13"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Mul(Sign(Ts_Return(close, 20)), Div(Abs(Ts_Return(close, 20)), Add(Ts_Sum(Abs(Returns), 20, 10), 0.000001))))"
ECONOMIC_HYPOTHESIS = "Direction combined with path efficiency distinguishes orderly trends from equally large but noisy moves."
TARGET_PATTERNS = "TrendEfficiency"
