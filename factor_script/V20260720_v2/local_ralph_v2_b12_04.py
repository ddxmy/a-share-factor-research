FACTOR_NAME = "Overnight_Total_Variance_Share"
FORMULA = "Neg(Cs_Rank(Div(Ts_Mean(Power(Div(Sub(open, pre_close), pre_close), 2), 60, 30), Add(Ts_Mean(Power(Returns, 2), 60, 30), 0.001))))"
ECONOMIC_HYPOTHESIS = "The fraction of total close-to-close variance attributable to overnight gaps measures structural overnight risk concentration."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

