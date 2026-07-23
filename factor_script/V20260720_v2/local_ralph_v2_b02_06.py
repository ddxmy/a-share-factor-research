FACTOR_NAME = "Wick_Variance_Asymmetry"
FORMULA = "Cs_Rank(Div(Ts_Mean(Power(Sub(Min(open, close), low), 2), 20, 10), Add(Ts_Mean(Power(Sub(high, Max(open, close)), 2), 20, 10), 0.001)))"
ECONOMIC_HYPOTHESIS = "The ratio of lower-wick to upper-wick energy measures asymmetric rejection pressure beyond average wick direction."
TARGET_PATTERNS = ["volatility_asymmetry"]

