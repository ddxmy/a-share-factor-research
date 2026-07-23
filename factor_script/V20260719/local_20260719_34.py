"""Breadth of positive daily returns over twenty days."""

FACTOR_NAME = "local_20260719_34"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Mean(Sign(Returns), 20, 10))"
ECONOMIC_HYPOTHESIS = "A trend supported by many small positive days differs from one caused by a single jump and may persist more reliably."
TARGET_PATTERNS = "TrendBreadth"
