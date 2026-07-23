FACTOR_NAME = "Smoothed_VWAP_Range_Anchor"
FORMULA = "Cs_Rank(Ts_EMA(Div(Sub(vwap, Div(Add(Ts_Max(high, 20, 10), Ts_Min(low, 20, 10)), 2)), Add(Sub(Ts_Max(high, 20, 10), Ts_Min(low, 20, 10)), 0.001)), 10, 5))"
ECONOMIC_HYPOTHESIS = "Smoothed VWAP location around the rolling range midpoint captures where traded consensus is anchored within the recent range."
TARGET_PATTERNS = ["range_location_anchoring"]

