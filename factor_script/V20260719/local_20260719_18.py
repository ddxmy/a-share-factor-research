"""Short-term reversal weighted toward low-volume moves."""

FACTOR_NAME = "local_20260719_18"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Mul(Ts_Return(close, 5), Inverse(Add(Div(Ts_Mean(volume, 5), Ts_Mean(volume, 20)), 0.2)))))"
ECONOMIC_HYPOTHESIS = "Price moves without broad participation are more likely to be temporary and reverse."
TARGET_PATTERNS = "LowParticipationReversal"
