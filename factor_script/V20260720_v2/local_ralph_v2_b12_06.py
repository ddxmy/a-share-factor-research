FACTOR_NAME = "Downside_Upside_Volatility_Transition"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(If(Less(Returns, 0), Power(Returns, 2), 0), Ts_Delay(If(Greater(Returns, 0), Power(Returns, 2), 0), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Cross-state dependence between downside variance and lagged upside variance measures asymmetric volatility-state transitions."
TARGET_PATTERNS = ["volatility_asymmetry"]

