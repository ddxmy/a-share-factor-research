FACTOR_NAME = "Downside_Expected_Shortfall"
FORMULA = "Cs_Rank(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Returns, 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "The rolling mean of returns beyond the stock's own downside-tail threshold measures persistent expected shortfall with low turnover."
TARGET_PATTERNS = ["return_tails_skewness"]

