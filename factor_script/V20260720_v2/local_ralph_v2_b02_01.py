FACTOR_NAME = "Gap_Prior_Intraday_Interaction"
FORMULA = "Neg(Cs_Rank(Mul(Div(Sub(open, pre_close), pre_close), Ts_Delay(Div(Sub(close, open), open), 1))))"
ECONOMIC_HYPOTHESIS = "An opening gap that extends the previous session's intraday direction reflects crowded continuation and is prone to reversal."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

