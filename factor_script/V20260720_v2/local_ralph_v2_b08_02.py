FACTOR_NAME = "Overnight_Intraday_Downside_Semibeta"
FORMULA = "Neg(Cs_Rank(Ts_Beta(If(Less(Div(Sub(open, pre_close), pre_close), 0), Abs(Div(Sub(open, pre_close), pre_close)), 0), If(Less(Div(Sub(close, open), open), 0), Abs(Div(Sub(close, open), open)), 0), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Rolling downside semibeta between overnight and intraday losses measures persistent cross-session fragility."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

