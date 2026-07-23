"""Persistent intraday return component."""

FACTOR_NAME = "local_20260719_17"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Div(Sub(close, open), open), 20, 10))"
ECONOMIC_HYPOTHESIS = "Separating the intraday component tests whether order-flow persistence differs from overnight information diffusion."
TARGET_PATTERNS = "IntradayDrift"
