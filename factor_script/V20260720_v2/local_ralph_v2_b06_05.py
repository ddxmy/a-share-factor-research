FACTOR_NAME = "Stable_Return_Turnover_Illiquidity"
FORMULA = "Neg(Cs_Rank(Div(Ts_Mean(Abs(Returns), 20, 10), Add(Ts_Mean(turn, 20, 10), 0.1))))"
ECONOMIC_HYPOTHESIS = "Persistent absolute return per unit of turnover measures structural illiquidity using slow-moving averages."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

