FACTOR_NAME = "Overnight_Attention_Reversal"
FORMULA = "Neg(Cs_Rank(Mul(Div(Sub(open, pre_close), pre_close), Div(amt, Ts_Mean(amt, 20, 10)))))"
ECONOMIC_HYPOTHESIS = "Overnight gaps accompanied by unusually high traded amount reflect attention-driven price pressure that partially reverses."
TARGET_PATTERNS = ["overnight_intraday_decomposition"]

