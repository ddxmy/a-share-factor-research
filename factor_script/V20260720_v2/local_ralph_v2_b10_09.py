FACTOR_NAME = "Gap_Range_Volatility_Coupling"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Abs(Div(Sub(open, pre_close), pre_close)), Div(Sub(high, low), pre_close), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Persistent coupling between absolute overnight gaps and intraday ranges measures cross-session volatility transmission."
TARGET_PATTERNS = ["volatility_asymmetry"]

