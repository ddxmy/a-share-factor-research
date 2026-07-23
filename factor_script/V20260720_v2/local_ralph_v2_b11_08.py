FACTOR_NAME = "Two_Sided_Tail_Curvature"
FORMULA = "Neg(Cs_Rank(Sub(Sub(Ts_Quantile(Returns, 60, 0.9, 30), Ts_Median(Returns, 60, 30)), Sub(Ts_Median(Returns, 60, 30), Ts_Quantile(Returns, 60, 0.1, 30)))))"
ECONOMIC_HYPOTHESIS = "Difference between upper- and lower-tail spreads captures asymmetric distribution curvature with a low-turnover quantile statistic."
TARGET_PATTERNS = ["return_tails_skewness"]

