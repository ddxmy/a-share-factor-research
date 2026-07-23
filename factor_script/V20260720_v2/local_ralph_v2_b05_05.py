FACTOR_NAME = "Turnover_Instability_Premium"
FORMULA = "Neg(Cs_Rank(Div(Ts_MAD(turn, 20, 10), Add(Ts_Median(turn, 20, 10), 0.1))))"
ECONOMIC_HYPOTHESIS = "Stocks with unstable turnover relative to their normal participation face intermittent liquidity and an unfavorable premium."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

