FACTOR_NAME = "Volatility_of_Volatility_Coefficient"
FORMULA = "Neg(Cs_Rank(Div(Ts_Std(Abs(Returns), 60, 30), Add(Ts_Mean(Abs(Returns), 60, 30), 0.001))))"
ECONOMIC_HYPOTHESIS = "Coefficient of variation of absolute returns measures instability in the volatility surface rather than its average level."
TARGET_PATTERNS = ["volatility_asymmetry"]

