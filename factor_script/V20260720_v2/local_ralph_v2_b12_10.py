FACTOR_NAME = "Local_Slope_State_Persistence"
FORMULA = "Cs_Rank(Mul(Sign(Slope(Log(close), 60)), Ts_Correlation(Slope(Log(close), 10), Ts_Delay(Slope(Log(close), 10), 10), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Signed persistence of local slope states captures durable nonlinear trend regimes rather than a single slope estimate."
TARGET_PATTERNS = ["conditional_regimes"]

