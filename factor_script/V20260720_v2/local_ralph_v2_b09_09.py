FACTOR_NAME = "Close_Return_Range_Variance_Ratio"
FORMULA = "Cs_Rank(Div(Ts_Mean(Power(Returns, 2), 60, 30), Add(Ts_Mean(Power(Div(Sub(high, low), pre_close), 2), 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "Close-to-close variance relative to intraday range variance separates gap-dominated risk from continuous trading volatility."
TARGET_PATTERNS = ["volatility_asymmetry"]

