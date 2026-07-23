"""Volatility-scaled log-price slope."""

FACTOR_NAME = "local_20260719_35"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Div(Slope(Log(close), 20), Add(Ts_Std(Returns, 20, 10), 0.001)))"
ECONOMIC_HYPOTHESIS = "A smooth log-price trend per unit of realized risk measures information diffusion rather than raw magnitude."
TARGET_PATTERNS = "RiskAdjustedTrendSlope"
