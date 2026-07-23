FACTOR_NAME = "Regression_Quality_Trend"
FORMULA = "Cs_Rank(Mul(Sign(Ts_Return(close, 20)), Ts_Rsquare(Log(close), Ts_WMA(Log(close), 5, 3), 20, 10)))"
ECONOMIC_HYPOTHESIS = "The direction of a trend is more reliable when prices closely follow a smooth path rather than oscillating around it."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

