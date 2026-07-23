FACTOR_NAME = "Range_Distribution_Skew"
FORMULA = "Neg(Cs_Rank(Ts_Skewness(Div(Sub(high, low), pre_close), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Skewness of normalized daily ranges captures whether volatility is dominated by occasional range explosions."
TARGET_PATTERNS = ["volatility_asymmetry"]

