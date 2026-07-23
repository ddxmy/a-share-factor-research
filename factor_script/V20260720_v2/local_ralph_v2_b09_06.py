FACTOR_NAME = "Robust_Subperiod_Drift"
FORMULA = "Cs_Rank(Div(Ts_Median(Ts_Return(close, 5), 60, 30), Add(Ts_MAD(Ts_Return(close, 5), 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "The median five-day return relative to its dispersion estimates persistent drift while resisting isolated endpoint moves."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

