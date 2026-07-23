FACTOR_NAME = "Decay_Signed_Amount_Pressure"
FORMULA = "Cs_Rank(Ts_DecayLinear(Mul(Sign(Sub(close, open)), Div(amt, Ts_Mean(amt, 20, 10))), 10, 5))"
ECONOMIC_HYPOTHESIS = "Recency-weighted signed abnormal amount measures persistent accumulation or distribution pressure."
TARGET_PATTERNS = ["signed_volume_accumulation"]

