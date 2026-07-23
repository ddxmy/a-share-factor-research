FACTOR_NAME = "Volatility_Turnover_Sensitivity"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Abs(Returns), turn, 60, 30)))"
ECONOMIC_HYPOTHESIS = "Slow-moving sensitivity of absolute returns to turnover measures whether participation shocks amplify volatility."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

