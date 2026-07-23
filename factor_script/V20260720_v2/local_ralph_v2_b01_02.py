FACTOR_NAME = "Gap_Intraday_Alignment"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Sign(Sub(close, open)), Div(Sub(open, pre_close), pre_close)), 20, 10))"
ECONOMIC_HYPOTHESIS = "Persistent alignment between overnight gaps and intraday direction identifies information continuation versus gap exhaustion."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

