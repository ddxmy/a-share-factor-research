"""Negative realized-return skewness preference."""

FACTOR_NAME = "local_20260719_07"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Skewness(Returns, 20, 10)))"
ECONOMIC_HYPOTHESIS = "Investors may overpay for positively skewed return profiles, leaving a short-horizon low-skew premium."
TARGET_PATTERNS = "LotteryPreference,ReturnSkewness"
