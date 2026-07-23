FACTOR_NAME = "Persistent_Illiquidity_Correlation"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Abs(Returns), Inverse(Add(amt, 1)), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Persistent co-movement of absolute returns with low traded amount identifies fragile liquidity and adverse price impact."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

