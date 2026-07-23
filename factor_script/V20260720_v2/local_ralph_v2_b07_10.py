FACTOR_NAME = "Tail_Risk_Damped_Overnight_Drift"
FORMULA = "Neg(Cs_Rank(Div(Ts_Mean(Div(Sub(open, pre_close), pre_close), 20, 10), Add(Ts_MAD(Returns, 60, 30), 0.001))))"
ECONOMIC_HYPOTHESIS = "Persistent overnight drift is more reliable after continuous damping by long-horizon tail-sensitive return dispersion."
TARGET_PATTERNS = ["conditional_regimes"]

