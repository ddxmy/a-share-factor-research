FACTOR_NAME = "Return_Turnover_Change_Disagreement"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Returns, Ts_Return(turn, 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "A negative relation between returns and changes in turnover indicates price moves unsupported by participation and likely correction."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

