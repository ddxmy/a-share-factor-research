FACTOR_NAME = "Persistent_Drawdown_Autocorrelation"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Div(Sub(Ts_Max(high, 20, 10), close), Add(Ts_Max(high, 20, 10), 0.001)), Ts_Delay(Div(Sub(Ts_Max(high, 20, 10), close), Add(Ts_Max(high, 20, 10), 0.001)), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Serial persistence of drawdown depth captures slow downside states without relying on daily close-location anchors."
TARGET_PATTERNS = ["return_tails_skewness"]

