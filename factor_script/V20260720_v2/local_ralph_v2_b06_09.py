FACTOR_NAME = "Rolling_Median_Price_Anchor"
FORMULA = "Neg(Cs_Rank(Div(Sub(close, Ts_Median(close, 20, 10)), Add(Ts_MAD(close, 20, 10), 0.001))))"
ECONOMIC_HYPOTHESIS = "Deviation from a robust rolling median price anchor, scaled by median absolute dispersion, identifies slowly evolving stretch."
TARGET_PATTERNS = ["range_location_anchoring"]

