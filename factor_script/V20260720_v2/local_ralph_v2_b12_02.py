FACTOR_NAME = "Amount_Turnover_Decoupling"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Ts_Return(amt, 1), Ts_Return(turn, 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Weak co-movement between changes in traded amount and turnover indicates price-driven amount shocks rather than broad participation."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

