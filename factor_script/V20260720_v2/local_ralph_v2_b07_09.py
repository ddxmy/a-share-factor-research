FACTOR_NAME = "Median_Close_Location_Anchor"
FORMULA = "Cs_Rank(Ts_Median(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), 60, 30))"
ECONOMIC_HYPOTHESIS = "The long-window median close location provides a robust, low-turnover measure of persistent buying or selling at daily extremes."
TARGET_PATTERNS = ["range_location_anchoring"]

