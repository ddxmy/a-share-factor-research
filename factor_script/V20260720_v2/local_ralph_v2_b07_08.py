FACTOR_NAME = "Down_Up_Range_Asymmetry"
FORMULA = "Neg(Cs_Rank(Div(Sub(Ts_Mean(If(Less(Returns, 0), Div(Sub(high, low), pre_close), 0), 60, 30), Ts_Mean(If(Greater(Returns, 0), Div(Sub(high, low), pre_close), 0), 60, 30)), Add(Ts_Mean(Div(Sub(high, low), pre_close), 60, 30), 0.001))))"
ECONOMIC_HYPOTHESIS = "Excess trading range on down days relative to up days measures slowly evolving downside volatility asymmetry."
TARGET_PATTERNS = ["volatility_asymmetry"]

