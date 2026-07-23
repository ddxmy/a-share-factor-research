"""Proximity to the sixty-day high."""

FACTOR_NAME = "local_20260719_32"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Div(close, Ts_Max(high, 60, 30)))"
ECONOMIC_HYPOTHESIS = "Proximity to a medium-horizon high captures anchored investor beliefs and slow information diffusion with lower turnover than a five-day location signal."
TARGET_PATTERNS = "Extended_Position_Location"
