FACTOR_NAME = "Median_Adjusted_Path_Efficiency"
FORMULA = "Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Sum(Abs(Sub(Returns, Ts_Median(Returns, 20, 10))), 20, 10), 0.000001)))"
ECONOMIC_HYPOTHESIS = "Net displacement relative to median-adjusted daily path noise rewards robust directional efficiency rather than endpoint luck."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

