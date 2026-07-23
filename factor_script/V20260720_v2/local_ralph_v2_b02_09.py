FACTOR_NAME = "Range_Position_High_Recency"
FORMULA = "Cs_Rank(Sub(Div(Sub(close, Ts_Min(low, 20, 10)), Add(Sub(Ts_Max(high, 20, 10), Ts_Min(low, 20, 10)), 0.001)), Div(Ts_ArgMax(high, 20, 10), 20)))"
ECONOMIC_HYPOTHESIS = "A high position in the recent range is stronger when the range high occurred recently, combining location with anchor freshness."
TARGET_PATTERNS = ["range_location_anchoring"]

