FACTOR_NAME = "Overnight_Move_Share_Reversal"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Div(Sub(open, pre_close), Add(Abs(Sub(close, pre_close)), 0.001)), 10, 5)))"
ECONOMIC_HYPOTHESIS = "A large overnight contribution to the total close-to-close move indicates opening-price pressure that tends to fade."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

