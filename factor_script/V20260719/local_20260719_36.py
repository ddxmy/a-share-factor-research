"""Twenty-day accumulation-distribution pressure."""

FACTOR_NAME = "local_20260719_36"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), Div(volume, Ts_Mean(volume, 20))), 20, 10))"
ECONOMIC_HYPOTHESIS = "Closes near the high on above-normal volume proxy for persistent accumulation rather than a one-day close-location effect."
TARGET_PATTERNS = "AccumulationDistribution,SignedVolumePressure"
