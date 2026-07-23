FACTOR_NAME = "Serial_Dependence_Weighted_Trend"
FORMULA = "Cs_Rank(Mul(Ts_Return(close, 20), Ts_Rsquare(Returns, Ts_Delay(Returns, 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Medium-horizon direction weighted by serial return dependence separates persistent paths from accidental endpoint moves."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

