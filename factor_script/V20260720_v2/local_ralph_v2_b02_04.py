FACTOR_NAME = "Return_Turnover_Residual_Pressure"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Ts_Residual(Returns, Ts_Return(turn, 1), 20, 10), 5, 3)))"
ECONOMIC_HYPOTHESIS = "Recent returns unexplained by changing turnover isolate unsupported price pressure that should mean-revert."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

