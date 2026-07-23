FACTOR_NAME = "Return_Turnover_Impulse_Disagreement"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Mul(Returns, Ts_Delta(turn, 1)), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Price moves repeatedly aligned with abrupt turnover changes indicate participation shocks rather than durable information."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

