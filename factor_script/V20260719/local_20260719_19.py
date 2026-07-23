"""Smoothed reversal of an Amihud-style illiquidity shock."""

FACTOR_NAME = "local_20260719_19"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Ts_ZScore(Div(Abs(Returns), Add(amt, 1)), 20, 10), 5, 3)))"
ECONOMIC_HYPOTHESIS = "Unusually large price impact per unit of trading amount signals temporary liquidity pressure that can mean-revert."
TARGET_PATTERNS = "LiquidityShockReversal"
