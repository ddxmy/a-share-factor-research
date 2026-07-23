"""Twenty-day normalized signed-volume balance."""

FACTOR_NAME = "local_20260719_37"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Sign(Returns), Div(volume, Ts_Mean(volume, 20))), 20, 10))"
ECONOMIC_HYPOTHESIS = "Persistent signed participation approximates cumulative order-flow imbalance with a slower-moving implementation."
TARGET_PATTERNS = "SignedVolumePressure"
