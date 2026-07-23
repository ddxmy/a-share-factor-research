FACTOR_NAME = "Normalized_On_Balance_Volume"
FORMULA = "Cs_Rank(Div(Ts_Sum(Mul(Sign(Returns), volume), 20, 10), Add(Ts_Sum(volume, 20, 10), 1)))"
ECONOMIC_HYPOTHESIS = "The fraction of recent volume occurring on up versus down days measures sustained accumulation or distribution."
TARGET_PATTERNS = ["signed_volume_accumulation"]

