FACTOR_NAME = "Downside_Tail_Volume_Pressure"
FORMULA = "Neg(Cs_Rank(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Div(volume, Ts_Mean(volume, 20, 10)), 0), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Repeated high-volume returns in the stock's own downside tail reveal forced selling and persistent weakness."
TARGET_PATTERNS = ["return_tails_skewness"]

