FACTOR_NAME = "Rolling_VWAP_Anchor_Displacement"
FORMULA = "Neg(Cs_Rank(Div(Sub(close, Ts_Mean(vwap, 20, 10)), Add(Ts_MAD(vwap, 20, 10), 0.001))))"
ECONOMIC_HYPOTHESIS = "Price displacement from its rolling VWAP anchor, normalized by typical anchor dispersion, captures stretched positioning."
TARGET_PATTERNS = ["range_location_anchoring"]

