FACTOR_NAME = "Downside_Tail_Clustering"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Abs(Returns), 0), Ts_Delay(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Abs(Returns), 0), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Serial clustering of downside-tail magnitudes captures persistent crash regimes rather than isolated extreme losses."
TARGET_PATTERNS = ["return_tails_skewness"]

