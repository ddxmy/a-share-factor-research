FACTOR_NAME = "Turnover_Supply_Range_Response"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Ts_Delay(Ts_ZScore(turn, 60, 30), 1), Div(Sub(high, low), pre_close), 60, 30)))"
ECONOMIC_HYPOTHESIS = "The historical range response to lagged turnover surprises measures whether added participation absorbs or amplifies volatility."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

