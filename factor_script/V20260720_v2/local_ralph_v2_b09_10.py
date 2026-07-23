FACTOR_NAME = "Absolute_Return_Clustering"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Abs(Returns), Ts_Delay(Abs(Returns), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Serial dependence in absolute returns captures persistent volatility regimes with a slow-moving, low-turnover statistic."
TARGET_PATTERNS = ["conditional_regimes"]

