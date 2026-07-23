FACTOR_NAME = "Residual_Overnight_Surprise"
FORMULA = "Neg(Cs_Rank(Ts_Residual(Div(Sub(open, pre_close), pre_close), Ts_Delay(Returns, 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "The component of an opening gap unexplained by the prior return isolates overnight surprise and temporary opening pressure."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

