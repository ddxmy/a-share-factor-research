FACTOR_NAME = "Lagged_Gap_Risk_Transmission"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Abs(Div(Sub(close, open), open)), Ts_Delay(Abs(Div(Sub(open, pre_close), pre_close)), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Intraday absolute-return sensitivity to prior overnight gap magnitude measures delayed transmission of overnight risk."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

