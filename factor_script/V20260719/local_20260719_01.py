"""Overnight gap reversal strengthened by unusual trading volume."""

FACTOR_NAME = "local_20260719_01"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Mul(Div(Sub(open, pre_close), pre_close), Div(volume, Ts_Mean(volume, 20)))))"
ECONOMIC_HYPOTHESIS = "Large overnight gaps accompanied by heavy volume may reflect opening overreaction that reverses subsequently."
TARGET_PATTERNS = "OvernightGapReversal,VolumeConfirmation"
