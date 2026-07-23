"""Directional efficiency of the recent price path."""

FACTOR_NAME = "local_20260719_08"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Div(Abs(Ts_Return(close, 20)), Add(Ts_Sum(Abs(Returns), 20, 10), 0.000001)))"
ECONOMIC_HYPOTHESIS = "A large net move relative to total path length indicates a cleaner, less noisy trend with greater continuation potential."
TARGET_PATTERNS = "TrendEfficiency"
