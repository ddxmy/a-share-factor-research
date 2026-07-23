FACTOR_NAME = "Overnight_Intraday_Tail_Dominance"
FORMULA = "Cs_Rank(Sub(Ts_Mean(If(Less(Div(Sub(open, pre_close), pre_close), Ts_Quantile(Div(Sub(open, pre_close), pre_close), 60, 0.1, 30)), Div(Sub(open, pre_close), pre_close), 0), 60, 30), Ts_Mean(If(Less(Div(Sub(close, open), open), Ts_Quantile(Div(Sub(close, open), open), 60, 0.1, 30)), Div(Sub(close, open), open), 0), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Relative expected shortfall in overnight versus intraday sessions identifies where a stock's downside risk is concentrated."
TARGET_PATTERNS = ["return_tails_skewness"]

