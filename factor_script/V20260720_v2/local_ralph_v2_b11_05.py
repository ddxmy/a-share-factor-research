FACTOR_NAME = "Volatility_Term_Curvature"
FORMULA = "Neg(Cs_Rank(Sub(Div(Ts_Std(Returns, 5, 3), Add(Ts_Std(Returns, 20, 10), 0.001)), Div(Ts_Std(Returns, 20, 10), Add(Ts_Std(Returns, 60, 30), 0.001)))))"
ECONOMIC_HYPOTHESIS = "Difference between short-to-medium and medium-to-long volatility ratios measures curvature of the realized volatility term structure."
TARGET_PATTERNS = ["volatility_asymmetry"]

