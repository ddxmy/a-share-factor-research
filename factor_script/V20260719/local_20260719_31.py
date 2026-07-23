"""Low-risk scaled twenty-day reversal."""

FACTOR_NAME = "local_20260719_31"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Std(Returns, 20, 10), 0.001))))"
ECONOMIC_HYPOTHESIS = "Price pressure relative to normal realized risk should reverse more reliably than an equally large but risk-proportionate move."
TARGET_PATTERNS = "MediumHorizonReversal,VolatilityScaling"
