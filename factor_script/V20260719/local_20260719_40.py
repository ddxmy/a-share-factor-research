"""Overnight drift scaled by total realized volatility."""

FACTOR_NAME = "local_20260719_40"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Div(Ts_Mean(Div(Sub(open, pre_close), pre_close), 20, 10), Add(Ts_Std(Returns, 20, 10), 0.001)))"
ECONOMIC_HYPOTHESIS = "Scaling persistent overnight pressure by total risk tests whether the effect reflects a compensation ratio rather than raw gaps."
TARGET_PATTERNS = "OvernightDrift,VolatilityScaling"
