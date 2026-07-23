FACTOR_NAME = "Smoothed_Gap_Per_Turnover"
FORMULA = "Neg(Cs_Rank(Ts_EMA(Div(Div(Sub(open, pre_close), pre_close), Add(turn, 0.1)), 10, 5)))"
ECONOMIC_HYPOTHESIS = "A smoothed overnight gap per unit of turnover captures persistent opening pressure while reducing day-to-day signal churn."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

