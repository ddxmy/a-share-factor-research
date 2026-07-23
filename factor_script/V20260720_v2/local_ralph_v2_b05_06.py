FACTOR_NAME = "Overnight_Intraday_Variance_Asymmetry"
FORMULA = "Neg(Cs_Rank(Div(Ts_Mean(Power(Div(Sub(open, pre_close), pre_close), 2), 20, 10), Add(Ts_Mean(Power(Div(Sub(close, open), open), 2), 20, 10), 0.001))))"
ECONOMIC_HYPOTHESIS = "Excess overnight variance relative to intraday variance reflects unresolved information and asymmetric gap risk."
TARGET_PATTERNS = ["volatility_asymmetry"]

