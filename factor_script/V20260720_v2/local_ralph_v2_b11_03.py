FACTOR_NAME = "Unexplained_Overnight_Risk"
FORMULA = "Neg(Cs_Rank(Ts_Std(Ts_Residual(Div(Sub(open, pre_close), pre_close), Div(Sub(close, open), open), 60, 30), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Volatility of overnight gaps unexplained by same-day intraday returns isolates persistent overnight-specific risk."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

