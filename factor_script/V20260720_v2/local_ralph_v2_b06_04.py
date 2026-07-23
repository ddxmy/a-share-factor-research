FACTOR_NAME = "Return_Amount_Impulse_Beta"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Returns, Ts_Delta(Log(amt), 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Return sensitivity to abrupt traded-amount changes isolates price moves driven by participation shocks rather than durable information."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

