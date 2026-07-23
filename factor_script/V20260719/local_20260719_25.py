"""Slow-moving Amihud-style illiquidity level."""

FACTOR_NAME = "local_20260719_25"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Div(Abs(Returns), Add(amt, 1)), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Persistent price impact per unit of amount measures costly liquidity; the sign is allowed to be learned in discovery."
TARGET_PATTERNS = "IlliquidityLevel"
