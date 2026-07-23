FACTOR_NAME = "Range_Turnover_Elasticity"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Ts_Delta(Div(Sub(high, low), pre_close), 1), Ts_Delta(turn, 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Sensitivity of range changes to turnover changes measures whether incremental liquidity supply compresses or expands trading ranges."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

