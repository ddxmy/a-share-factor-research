FACTOR_NAME = "Prior_Location_Conditioned_Gap"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Mul(Div(Sub(open, pre_close), pre_close), Ts_Delay(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), 1)), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Overnight gaps that extend a prior strong closing location reflect crowded cross-session continuation and tend to mean-revert."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

