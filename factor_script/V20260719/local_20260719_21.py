"""Signal-to-noise ratio of persistent overnight returns."""

FACTOR_NAME = "local_20260719_21"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Div(Ts_Mean(Div(Sub(open, pre_close), pre_close), 20, 10), Add(Ts_Std(Div(Sub(open, pre_close), pre_close), 20, 10), 0.000001)))"
ECONOMIC_HYPOTHESIS = "Scaling overnight drift by its own variation separates persistent outside-hours pressure from isolated gaps."
TARGET_PATTERNS = "OvernightDrift,SignalToNoise"
