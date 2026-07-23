"""Down-day abnormal-volume pressure."""

FACTOR_NAME = "local_20260719_39"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Mean(If(Less(Returns, 0), Div(volume, Ts_Mean(volume, 20)), 0), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Persistent abnormal volume on negative-return days captures forced selling or informed distribution."
TARGET_PATTERNS = "DownsideVolumePressure"
