"""Upside-to-downside semivariance balance."""

FACTOR_NAME = "local_20260719_15"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Div(Ts_Mean(If(Greater(Returns, 0), Power(Returns, 2), 0), 20, 10), Add(Ts_Mean(If(Less(Returns, 0), Power(Returns, 2), 0), 20, 10), 0.000001)))"
ECONOMIC_HYPOTHESIS = "The balance of upside and downside variation distinguishes constructive volatility from downside-dominated risk."
TARGET_PATTERNS = "SemivarianceAsymmetry"
