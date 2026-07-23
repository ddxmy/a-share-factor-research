"""Low downside-semivariance effect."""

FACTOR_NAME = "local_20260719_05"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Mean(If(Less(Returns, 0), Power(Returns, 2), 0), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Stocks with concentrated downside variation require greater risk compensation and may underperform over short horizons after risk neutralization."
TARGET_PATTERNS = "DownsideRisk,LowVolatility"
