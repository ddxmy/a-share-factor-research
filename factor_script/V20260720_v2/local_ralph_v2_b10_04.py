FACTOR_NAME = "Two_Sided_Gap_Absorption"
FORMULA = "Cs_Rank(Ts_Mean(If(Less(Div(Sub(open, pre_close), pre_close), 0), Div(Div(Sub(close, open), open), Add(Abs(Div(Sub(open, pre_close), pre_close)), 0.001)), If(Greater(Div(Sub(open, pre_close), pre_close), 0), Neg(Div(Div(Sub(close, open), open), Add(Abs(Div(Sub(open, pre_close), pre_close)), 0.001))), 0)), 60, 30))"
ECONOMIC_HYPOTHESIS = "A unified two-sided measure rewards intraday recovery after negative gaps and fading after positive gaps."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

