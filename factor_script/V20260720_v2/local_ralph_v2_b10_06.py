FACTOR_NAME = "Rank_Monotonicity_Trend"
FORMULA = "Cs_Rank(Mul(Sign(Slope(Log(close), 60)), Ts_Rsquare(Log(close), Ts_Rank(Log(close), 60, 30), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Signed fit between log price and its rolling ordinal position measures monotonic trend structure rather than endpoint momentum."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

