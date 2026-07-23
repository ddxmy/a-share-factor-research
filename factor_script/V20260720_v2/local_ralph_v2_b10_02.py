FACTOR_NAME = "Subperiod_Return_Skewness"
FORMULA = "Neg(Cs_Rank(Ts_Skewness(Ts_Return(close, 5), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Skewness of overlapping five-day returns captures medium-horizon tail asymmetry beyond single-day extreme events."
TARGET_PATTERNS = ["return_tails_skewness"]

