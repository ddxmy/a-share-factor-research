"""Short-lag return autocorrelation regime."""

FACTOR_NAME = "local_20260719_27"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Returns, Ts_Delay(Returns, 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Return autocorrelation distinguishes persistent information diffusion from alternating liquidity-driven price pressure."
TARGET_PATTERNS = "ReturnAutocorrelation"
