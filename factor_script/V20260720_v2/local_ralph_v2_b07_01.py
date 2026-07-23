FACTOR_NAME = "Robust_Overnight_Gap_Surprise"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Div(Sub(Div(Sub(open, pre_close), pre_close), Ts_Median(Div(Sub(open, pre_close), pre_close), 60, 30)), Add(Ts_MAD(Div(Sub(open, pre_close), pre_close), 60, 30), 0.001)), 5, 3)))"
ECONOMIC_HYPOTHESIS = "A smoothed gap surprise relative to each stock's own median and MAD isolates unusual overnight pressure while limiting churn."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

