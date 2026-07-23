"""Turnover-adjusted twenty-day reversal."""

FACTOR_NAME = "local_20260719_24"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Mean(turn, 20, 10), 0.1))))"
ECONOMIC_HYPOTHESIS = "A given price move supported by little turnover is more likely to be temporary than a broadly traded move."
TARGET_PATTERNS = "MediumHorizonReversal,LiquidityScaling"
