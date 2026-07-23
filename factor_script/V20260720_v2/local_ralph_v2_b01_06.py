FACTOR_NAME = "Amount_Shock_Price_Impact"
FORMULA = "Neg(Cs_Rank(Mul(Ts_ZScore(Log(amt), 20, 10), Abs(Returns))))"
ECONOMIC_HYPOTHESIS = "Large absolute price changes occurring with abnormal traded amount proxy costly liquidity demand and subsequent impact reversal."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

