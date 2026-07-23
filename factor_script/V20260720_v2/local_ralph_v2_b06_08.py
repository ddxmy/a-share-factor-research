FACTOR_NAME = "Location_Amount_Change_Accumulation"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), Sign(Ts_Delta(amt, 1))), 20, 10))"
ECONOMIC_HYPOTHESIS = "Close location aligned with changes in traded amount distinguishes accumulation and distribution without reproducing OBV."
TARGET_PATTERNS = ["signed_volume_accumulation"]

