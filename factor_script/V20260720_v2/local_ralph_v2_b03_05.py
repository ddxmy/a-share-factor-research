FACTOR_NAME = "Lagged_Impact_Recovery"
FORMULA = "Cs_Rank(Ts_Mean(Mul(Neg(Sign(Returns)), Ts_Delay(Div(Abs(Returns), Add(amt, 1)), 1)), 5, 3))"
ECONOMIC_HYPOTHESIS = "Price moves following prior high price impact tend to reverse as temporary liquidity demand is absorbed."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

