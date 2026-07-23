FACTOR_NAME = "Close_Location_Stability"
FORMULA = "Neg(Cs_Rank(Ts_MAD(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Low dispersion of daily close location indicates a stable trading anchor rather than sporadic closing pressure."
TARGET_PATTERNS = ["range_location_anchoring"]

