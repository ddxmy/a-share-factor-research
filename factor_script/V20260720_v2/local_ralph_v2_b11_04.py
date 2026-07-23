FACTOR_NAME = "Nonlinear_Gap_Pass_Through"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Div(Sub(close, open), open), SignedPower(Div(Sub(open, pre_close), pre_close), 2), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Intraday sensitivity to signed squared gaps measures nonlinear cross-session pass-through during larger overnight shocks."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

