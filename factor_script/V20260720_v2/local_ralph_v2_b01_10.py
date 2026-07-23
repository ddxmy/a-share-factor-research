FACTOR_NAME = "Turnover_Weighted_Close_Location"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), Div(turn, Ts_Mean(turn, 20, 10))), 10, 5))"
ECONOMIC_HYPOTHESIS = "Close location within the daily range is more informative when confirmed by abnormal turnover."
TARGET_PATTERNS = ["range_location_anchoring"]

