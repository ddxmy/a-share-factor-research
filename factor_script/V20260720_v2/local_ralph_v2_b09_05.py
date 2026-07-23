FACTOR_NAME = "EMA_Residual_Path_Efficiency"
FORMULA = "Cs_Rank(Div(Ts_Return(close, 60), Add(Ts_MAD(Div(Sub(close, Ts_EMA(close, 20, 10)), Ts_EMA(close, 20, 10)), 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "Long-horizon displacement relative to typical deviations from a moving path identifies trends that travel efficiently around a smooth trajectory."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

