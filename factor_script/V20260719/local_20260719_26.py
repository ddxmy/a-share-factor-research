"""Rolling association between returns and turnover."""

FACTOR_NAME = "local_20260719_26"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Returns, turn, 20, 10)))"
ECONOMIC_HYPOTHESIS = "Repeated high-turnover price advances can reveal crowded demand and subsequent reversal, while divergence may signal informed trading."
TARGET_PATTERNS = "ReturnTurnoverDivergence"
