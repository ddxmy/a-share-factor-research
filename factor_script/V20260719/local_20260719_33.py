"""Recency of the sixty-day high."""

FACTOR_NAME = "local_20260719_33"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_ArgMax(high, 60, 30)))"
ECONOMIC_HYPOTHESIS = "A recently established high indicates fresher information than an equally distant price ratio and changes discretely rather than every day."
TARGET_PATTERNS = "HighRecency"
