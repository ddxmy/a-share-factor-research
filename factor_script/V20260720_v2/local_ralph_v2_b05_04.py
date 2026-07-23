FACTOR_NAME = "Return_Amount_Surprise_Disagreement"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Returns, Ts_ZScore(Log(amt), 20, 10), 20, 10)))"
ECONOMIC_HYPOTHESIS = "A persistent relationship between returns and abnormal amount signals attention-driven moves that are vulnerable to correction."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

