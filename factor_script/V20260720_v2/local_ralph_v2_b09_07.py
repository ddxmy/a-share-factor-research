FACTOR_NAME = "Price_Impact_Mean_Reversion"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Div(Abs(Returns), Add(turn, 0.1)), Ts_Delay(Div(Abs(Returns), Add(turn, 0.1)), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Negative persistence in return-per-turnover price impact indicates replenishing liquidity supply after demand shocks."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

