FACTOR_NAME = "Turnover_Drought_Replenishment"
FORMULA = "Cs_Rank(Ts_Mean(If(Less(Ts_Delay(turn, 1), Ts_Delay(Ts_Quantile(turn, 60, 0.2, 30), 1)), Ts_Return(turn, 1), 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "Average turnover rebound immediately after stock-specific participation droughts measures the reliability of liquidity replenishment."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

