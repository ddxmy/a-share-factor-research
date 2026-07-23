FACTOR_NAME = "Gap_Intraday_Offset_Correlation"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Div(Sub(open, pre_close), pre_close), Div(Sub(close, open), open), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Persistent offsetting between overnight and intraday returns reveals systematic gap correction with a naturally smoothed signal."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

