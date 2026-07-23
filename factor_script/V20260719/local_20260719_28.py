"""Intermediate-versus-long volatility compression."""

FACTOR_NAME = "local_20260719_28"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Div(Ts_Std(Returns, 20, 10), Add(Ts_Std(Returns, 60, 30), 0.000001))))"
ECONOMIC_HYPOTHESIS = "Recent volatility compression relative to a longer baseline can identify stabilizing price discovery and lower inventory risk."
TARGET_PATTERNS = "VolatilityCompression"
