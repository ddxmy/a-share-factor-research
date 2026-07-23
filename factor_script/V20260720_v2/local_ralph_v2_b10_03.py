FACTOR_NAME = "Negative_Gap_Recovery_Efficiency"
FORMULA = "Cs_Rank(Ts_Mean(If(Less(Div(Sub(open, pre_close), pre_close), 0), Div(Div(Sub(close, open), open), Add(Abs(Div(Sub(open, pre_close), pre_close)), 0.001)), 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "Average intraday recovery per unit of negative opening gap measures cross-session risk absorption efficiency."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

