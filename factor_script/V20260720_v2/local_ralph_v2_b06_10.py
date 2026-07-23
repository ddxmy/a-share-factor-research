FACTOR_NAME = "Tail_Damped_Path_Slope"
FORMULA = "Cs_Rank(Div(Slope(Log(close), 20), Add(Abs(Ts_Skewness(Returns, 60, 30)), 1)))"
ECONOMIC_HYPOTHESIS = "Trend slope is more trustworthy when recent return-tail asymmetry is modest; continuous damping avoids regime-switch turnover."
TARGET_PATTERNS = ["conditional_regimes"]

