"""Maximum daily return lottery-demand effect."""

FACTOR_NAME = "local_20260719_06"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Max(Returns, 20, 10)))"
ECONOMIC_HYPOTHESIS = "Recent extreme positive returns attract lottery-like demand and can predict subsequent underperformance."
TARGET_PATTERNS = "LotteryPreference,ReturnTail"
