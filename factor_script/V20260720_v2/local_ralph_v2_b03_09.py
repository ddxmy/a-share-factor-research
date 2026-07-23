FACTOR_NAME = "VWAP_Anchored_Range_Support"
FORMULA = "Cs_Rank(Mul(Neg(Abs(Div(Sub(close, vwap), vwap))), Div(Sub(close, Ts_Min(low, 20, 10)), Add(Sub(Ts_Max(high, 20, 10), Ts_Min(low, 20, 10)), 0.001))))"
ECONOMIC_HYPOTHESIS = "A high range position near the session VWAP indicates broad support rather than an unstable closing spike."
TARGET_PATTERNS = ["range_location_anchoring"]

