FACTOR_NAME = "Overnight_Downside_Expected_Shortfall"
FORMULA = "Cs_Rank(Ts_Mean(If(Less(Div(Sub(open, pre_close), pre_close), Ts_Quantile(Div(Sub(open, pre_close), pre_close), 60, 0.1, 30)), Div(Sub(open, pre_close), pre_close), 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "The rolling mean of extreme negative overnight gaps measures low-frequency overnight crash exposure."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

