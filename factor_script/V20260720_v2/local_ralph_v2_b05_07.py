FACTOR_NAME = "Upper_Lower_Tail_Imbalance"
FORMULA = "Neg(Cs_Rank(Sub(Ts_Quantile(Returns, 60, 0.9, 30), Abs(Ts_Quantile(Returns, 60, 0.1, 30)))))"
ECONOMIC_HYPOTHESIS = "The difference between upside and downside tail magnitudes captures persistent lottery preference versus crash exposure."
TARGET_PATTERNS = ["return_tails_skewness"]

