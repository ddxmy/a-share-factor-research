"""Price trend minus normalized signed-volume trend."""

FACTOR_NAME = "local_20260719_38"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Sub(Ts_Return(close, 20), Ts_Mean(Mul(Sign(Returns), Div(volume, Ts_Mean(volume, 20))), 20, 10)))"
ECONOMIC_HYPOTHESIS = "A mismatch between price movement and cumulative signed participation can identify unsupported trends or hidden absorption."
TARGET_PATTERNS = "PriceVolumeDivergence,SignedVolumePressure"
