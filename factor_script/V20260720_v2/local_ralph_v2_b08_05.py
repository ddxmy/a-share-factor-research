FACTOR_NAME = "Recent_Downside_Tail_Concentration"
FORMULA = "Neg(Cs_Rank(Div(Ts_DecayExp(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Abs(Returns), 0), 60, 30), Add(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Abs(Returns), 0), 60, 30), 0.001))))"
ECONOMIC_HYPOTHESIS = "The recency-weighted share of downside-tail magnitude distinguishes active crash clustering from distant historical tail events."
TARGET_PATTERNS = ["return_tails_skewness"]

