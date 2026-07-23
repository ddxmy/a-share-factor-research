FACTOR_NAME = "Residual_Impact_Persistence"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Ts_Residual(Abs(Returns), turn, 60, 30), Ts_Delay(Ts_Residual(Abs(Returns), turn, 60, 30), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Autocorrelation of volatility unexplained by turnover isolates persistence in idiosyncratic liquidity impact and supply recovery."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

