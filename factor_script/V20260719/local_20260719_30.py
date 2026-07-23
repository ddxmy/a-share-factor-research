"""Range-risk-adjusted twenty-day reversal."""

FACTOR_NAME = "local_20260719_30"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Mean(Div(Sub(high, low), pre_close), 20, 10), 0.001))))"
ECONOMIC_HYPOTHESIS = "Scaling a medium-short return by realized trading range distinguishes price pressure from moves commensurate with normal risk."
TARGET_PATTERNS = "MediumHorizonReversal,RangeRiskScaling"
