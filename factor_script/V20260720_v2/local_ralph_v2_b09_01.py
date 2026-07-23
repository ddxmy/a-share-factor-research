FACTOR_NAME = "Consecutive_Downside_Severity"
FORMULA = "Neg(Cs_Rank(Ts_Mean(If(And(Less(Returns, 0), Less(Ts_Delay(Returns, 1), 0)), Abs(Returns), 0), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Average loss severity during consecutive down days measures persistent downside states rather than isolated tail events."
TARGET_PATTERNS = ["return_tails_skewness"]

