FACTOR_NAME = "Post_Tail_Recovery_Response"
FORMULA = "Cs_Rank(Ts_Mean(If(Less(Ts_Delay(Returns, 1), Ts_Delay(Ts_Quantile(Returns, 60, 0.1, 30), 1)), Returns, 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "The average realized response after a stock-specific downside-tail event measures its historical capacity to recover liquidity and price."
TARGET_PATTERNS = ["return_tails_skewness"]

