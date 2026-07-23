FACTOR_NAME = "Overnight_Intraday_Coskew"
FORMULA = "Neg(Cs_Rank(Ts_Covariance(SignedPower(Div(Sub(open, pre_close), pre_close), 2), Div(Sub(close, open), open), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Covariance of signed squared overnight gaps with intraday returns captures nonlinear cross-session coskewness."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

