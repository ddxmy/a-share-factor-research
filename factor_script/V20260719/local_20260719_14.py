"""Twenty-day total realized volatility effect."""

FACTOR_NAME = "local_20260719_14"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Std(Returns, 20, 10)))"
ECONOMIC_HYPOTHESIS = "The low-volatility anomaly can survive size and industry controls and naturally produces a slower-moving signal."
TARGET_PATTERNS = "LowVolatility"
