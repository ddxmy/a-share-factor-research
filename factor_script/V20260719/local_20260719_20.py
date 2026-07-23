"""Short-term reversal conditional on recent trading amount."""

FACTOR_NAME = "local_20260719_20"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Mul(Ts_Return(close, 5), Div(Ts_Mean(amt, 5), Ts_Mean(amt, 20)))))"
ECONOMIC_HYPOTHESIS = "Recent price moves accompanied by concentrated trading amount can reflect temporary inventory pressure and subsequently reverse."
TARGET_PATTERNS = "AmountConfirmedReversal"
