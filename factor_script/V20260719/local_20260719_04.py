"""Persistent signed volume pressure inferred from candle direction."""

FACTOR_NAME = "local_20260719_04"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Sign(Sub(close, open)), Div(volume, Ts_Mean(volume, 20))), 10, 5))"
ECONOMIC_HYPOTHESIS = "Repeated high-volume closes in the same direction proxy for persistent order-flow imbalance."
TARGET_PATTERNS = "SignedVolumePressure"
