FACTOR_NAME = "Worst_Subperiod_Loss"
FORMULA = "Cs_Rank(Div(Ts_Min(Ts_Return(close, 5), 60, 30), Add(Ts_MAD(Ts_Return(close, 5), 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "Worst five-day loss normalized by typical five-day dispersion captures robust downside capacity without averaging tail events."
TARGET_PATTERNS = ["return_tails_skewness"]

