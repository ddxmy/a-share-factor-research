FACTOR_NAME = "Signed_Extreme_Return_Mean"
FORMULA = "Neg(Cs_Rank(Ts_Mean(If(Greater(Abs(Returns), Ts_Quantile(Abs(Returns), 60, 0.9, 30)), Returns, 0), 20, 10)))"
ECONOMIC_HYPOTHESIS = "The signed average of self-defined extreme returns captures whether lottery gains or crash losses dominate recent tail attention."
TARGET_PATTERNS = ["return_tails_skewness"]

