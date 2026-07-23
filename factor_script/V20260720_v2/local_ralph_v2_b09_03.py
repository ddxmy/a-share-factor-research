FACTOR_NAME = "Gap_Loss_Intraday_Recovery_Coupling"
FORMULA = "Cs_Rank(Ts_Correlation(If(Less(Div(Sub(open, pre_close), pre_close), 0), Abs(Div(Sub(open, pre_close), pre_close)), 0), If(Greater(Div(Sub(close, open), open), 0), Div(Sub(close, open), open), 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "Persistent coupling of negative opening gaps with positive intraday recovery identifies reliable cross-session risk absorption."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

