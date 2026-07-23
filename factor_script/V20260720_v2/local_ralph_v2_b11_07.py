FACTOR_NAME = "Lower_Tail_Quantile_Curvature"
FORMULA = "Neg(Cs_Rank(Sub(Div(Add(Ts_Quantile(Returns, 60, 0.1, 30), Ts_Quantile(Returns, 60, 0.25, 30)), 2), Ts_Median(Returns, 60, 30))))"
ECONOMIC_HYPOTHESIS = "The average lower-tail quantile distance from the median measures broad downside curvature rather than only expected shortfall."
TARGET_PATTERNS = ["return_tails_skewness"]

