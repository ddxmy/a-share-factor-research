"""Medium-term momentum excluding the most recent week."""

FACTOR_NAME = "local_20260719_12"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Ts_Return(Ts_Delay(close, 5), 55))"
ECONOMIC_HYPOTHESIS = "Skipping the latest week separates slow information diffusion from very-short-horizon reversal and lowers turnover."
TARGET_PATTERNS = "SkipRecentMomentum"
