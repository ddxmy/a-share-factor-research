FACTOR_NAME = "Range_Amount_Absorption"
FORMULA = "Neg(Cs_Rank(Ts_Mean(Div(Div(Sub(high, low), pre_close), Add(Log(amt), 1)), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Wide ranges per unit of log traded amount reveal poor absorption and fragile liquidity."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

